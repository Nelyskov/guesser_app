"""
Price Guesser — FastAPI backend
Endpoints:
  GET  /api/product/random        — случайный товар для режима "угадай цену"
  GET  /api/product/pair          — два товара для режима "что дороже"
  POST /api/score                 — сохранить результат раунда
  GET  /api/leaderboard           — топ результатов
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
import os
import random

app = FastAPI(title="Price Guesser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── DB ───────────────────────────────────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "price_guesser"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def init_scores_table():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scores (
                    id         SERIAL PRIMARY KEY,
                    mode       TEXT    NOT NULL,  -- 'slider' | 'higher'
                    nickname   TEXT    NOT NULL DEFAULT 'Аноним',
                    score      INTEGER NOT NULL,
                    rounds     INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_scores_mode
                    ON scores(mode, score DESC);
            """)
        conn.commit()


@app.on_event("startup")
def startup():
    init_scores_table()


# ── Models ───────────────────────────────────────────────────────
class ScoreIn(BaseModel):
    mode:     str   # 'slider' | 'higher'
    nickname: str = "Аноним"
    score:    int
    rounds:   int


# ── Helpers ──────────────────────────────────────────────────────
def row_to_product(row: dict) -> dict:
    return {
        "id":        row["id"],
        "name":      row["name"],
        "price":     row["price"],
        "image_url": row["image_url"],
        "site":      row["site"],
    }


def fetch_random_products(n: int = 1) -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, name, price, image_url, site
                FROM products
                WHERE image_url IS NOT NULL AND image_url != ''
                  AND price > 0
                ORDER BY RANDOM()
                LIMIT %s
            """, (n,))
            rows = cur.fetchall()
    if len(rows) < n:
        raise HTTPException(status_code=404,
            detail="Недостаточно товаров в базе. Запусти парсер.")
    return [row_to_product(r) for r in rows]


# ── Endpoints ────────────────────────────────────────────────────
@app.get("/api/product/random")
def get_random_product():
    """Случайный товар для режима «угадай цену»."""
    products = fetch_random_products(1)
    p = products[0]
    # Возвращаем без цены — фронт покажет её только после ответа
    return {
        "id":        p["id"],
        "name":      p["name"],
        "image_url": p["image_url"],
        "site":      p["site"],
        "price_min": 0,
        "price_max": 0,  # фронт вычислит диапазон ползунка
    }


@app.get("/api/product/{product_id}/price")
def get_product_price(product_id: int):
    """Настоящая цена товара — запрашивается после ответа игрока."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT price FROM products WHERE id = %s", (product_id,))
            row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return {"price": row["price"]}


@app.get("/api/product/pair")
def get_product_pair():
    """Пара товаров для режима «что дороже»."""
    products = fetch_random_products(2)
    # Убеждаемся что цены разные
    attempts = 0
    while products[0]["price"] == products[1]["price"] and attempts < 5:
        products = fetch_random_products(2)
        attempts += 1
    return {
        "left":  {k: v for k, v in products[0].items() if k != "price"},
        "right": {k: v for k, v in products[1].items() if k != "price"},
    }


@app.get("/api/product/pair/reveal/{left_id}/{right_id}")
def reveal_pair(left_id: int, right_id: int):
    """Раскрыть цены пары после ответа."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, price FROM products WHERE id = ANY(%s)",
                ([left_id, right_id],))
            rows = {r["id"]: r["price"] for r in cur.fetchall()}
    return {
        "left_price":  rows.get(left_id, 0),
        "right_price": rows.get(right_id, 0),
    }


@app.post("/api/score")
def save_score(data: ScoreIn):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO scores (mode, nickname, score, rounds)
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (data.mode, data.nickname[:32], data.score, data.rounds))
            new_id = cur.fetchone()[0]
        conn.commit()
    return {"id": new_id, "saved": True}


@app.get("/api/leaderboard/{mode}")
def get_leaderboard(mode: str, limit: int = 10):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT nickname, score, rounds,
                       to_char(created_at, 'DD.MM.YYYY') AS date
                FROM scores
                WHERE mode = %s
                ORDER BY score DESC
                LIMIT %s
            """, (mode, limit))
            rows = cur.fetchall()
    return {"leaderboard": [dict(r) for r in rows]}


@app.get("/api/stats")
def get_stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT site) as sites,
                       AVG(price)::int as avg_price
                FROM products
                WHERE image_url != '' AND price > 0
            """)
            row = cur.fetchone()
    return {"total": row[0], "sites": row[1], "avg_price": row[2] or 0}
