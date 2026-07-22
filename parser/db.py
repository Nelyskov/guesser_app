"""
Database layer — PostgreSQL via psycopg2
Tables:
  products(id SERIAL, ext_id TEXT, site TEXT, name TEXT,
           price INT, image_url TEXT, scraped_at TIMESTAMP)
"""

import psycopg2
import psycopg2.extras
from typing import Optional


class Database:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.conn = psycopg2.connect(
            host    =cfg["host"],
            port    =cfg["port"],
            dbname  =cfg["dbname"],
            user    =cfg["user"],
            password=cfg["password"],
        )
        self.conn.autocommit = True

    # ── schema ──────────────────────────────────────────────────
    def init_schema(self):
        with self.conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id          SERIAL PRIMARY KEY,
                    ext_id      TEXT        NOT NULL,
                    site        TEXT        NOT NULL,
                    name        TEXT        NOT NULL,
                    price       INTEGER     NOT NULL,
                    image_url   TEXT        NOT NULL DEFAULT '',
                    scraped_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (ext_id, site)
                );
                CREATE INDEX IF NOT EXISTS idx_products_site
                    ON products(site);
                CREATE INDEX IF NOT EXISTS idx_products_price
                    ON products(price);
            """)

    # ── write ────────────────────────────────────────────────────
    def upsert_product(self, p: dict):
        """Insert or update a product. p must contain:
           ext_id, site, name, price, image_url
        """
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO products (ext_id, site, name, price, image_url, scraped_at)
                VALUES (%(ext_id)s, %(site)s, %(name)s, %(price)s,
                        %(image_url)s, NOW())
                ON CONFLICT (ext_id, site) DO UPDATE
                    SET name       = EXCLUDED.name,
                        price      = EXCLUDED.price,
                        image_url  = EXCLUDED.image_url,
                        scraped_at = NOW();
            """, p)

    # ── read ─────────────────────────────────────────────────────
    def get_all_products(self, limit: int = 2000) -> list[dict]:
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT id, ext_id, site, name, price, image_url, scraped_at
                FROM products
                ORDER BY scraped_at DESC
                LIMIT %s
            """, (limit,))
            return [dict(r) for r in cur.fetchall()]

    def get_stats(self) -> dict:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*)            AS total,
                    COUNT(DISTINCT site) AS sites,
                    COALESCE(AVG(price), 0)  AS avg_price,
                    COALESCE(MIN(price), 0)  AS min_price,
                    COALESCE(MAX(price), 0)  AS max_price
                FROM products
            """)
            row = cur.fetchone()
            if not row:
                return {}
            return {
                "total":     row[0],
                "sites":     row[1],
                "avg_price": float(row[2]),
                "min_price": row[3],
                "max_price": row[4],
            }

    def get_stats_by_site(self) -> list[tuple]:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT site, COUNT(*) AS cnt, AVG(price) AS avg_price
                FROM products
                GROUP BY site
                ORDER BY cnt DESC
            """)
            return cur.fetchall()

    def close(self):
        self.conn.close()
