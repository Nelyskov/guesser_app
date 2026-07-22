"""
Parser CLI — запускается вручную через Portainer или командную строку.
Использует те же парсеры что и GUI версия.

Примеры:
  python run.py --site wildberries --query кроссовки --max 100
  python run.py --site lamoda --query куртки --max 50 --min-price 1000
  python run.py --site tsum --query сумки --max 30
  python run.py --list   # показать доступные сайты
"""

import argparse
import os
import sys

# Настройки БД из переменных окружения (Docker передаёт их автоматически)
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "price_guesser"),
    "user":     os.getenv("DB_USER",     "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
}

SITES = ["wildberries", "ozon", "lamoda", "tsum"]


def log(msg: str, level: str = "info"):
    prefix = {
        "info":    "  ",
        "success": "✓ ",
        "warn":    "⚠ ",
        "error":   "✗ ",
        "dim":     "  ",
        "accent":  "→ ",
    }.get(level, "  ")
    print(f"{prefix}{msg}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Price Guesser Parser CLI")
    parser.add_argument("--site",      type=str, help="Сайт для парсинга")
    parser.add_argument("--query",     type=str, help="Поисковый запрос")
    parser.add_argument("--max",       type=int, default=100, help="Макс. товаров (default: 100)")
    parser.add_argument("--min-price", type=int, default=500,  help="Мин. цена ₽ (default: 500)")
    parser.add_argument("--max-price", type=int, default=0,    help="Макс. цена ₽ (default: 0=без ограничений)")
    parser.add_argument("--delay",     type=float, default=1.5, help="Задержка между запросами (default: 1.5)")
    parser.add_argument("--no-face-filter", action="store_true", help="Отключить фильтр лиц")
    parser.add_argument("--no-text-filter", action="store_true", help="Отключить фильтр текста")
    parser.add_argument("--list",      action="store_true", help="Показать доступные сайты")
    args = parser.parse_args()

    if args.list:
        print("Доступные сайты:")
        for s in SITES:
            print(f"  {s}")
        return

    if not args.site or not args.query:
        parser.print_help()
        sys.exit(1)

    site = args.site.lower()
    if site not in SITES:
        print(f"Неизвестный сайт: {site}. Доступные: {', '.join(SITES)}")
        sys.exit(1)

    # Импортируем нужный парсер
    from parsers.wildberries import WildberriesParser
    from parsers.ozon        import OzonParser
    from parsers.lamoda      import LamodaParser
    from parsers.tsum        import TsumParser

    PARSER_MAP = {
        "wildberries": WildberriesParser,
        "ozon":        OzonParser,
        "lamoda":      LamodaParser,
        "tsum":        TsumParser,
    }
    ParserCls = PARSER_MAP[site]

    # Подключаемся к БД
    import psycopg2
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        # Создаём таблицу если нет
        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id         SERIAL PRIMARY KEY,
                ext_id     TEXT NOT NULL,
                site       TEXT NOT NULL,
                name       TEXT NOT NULL,
                price      INTEGER NOT NULL,
                image_url  TEXT NOT NULL DEFAULT '',
                scraped_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE (ext_id, site)
            )
        """)
        log(f"БД подключена: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}", "success")
    except Exception as e:
        log(f"Ошибка подключения к БД: {e}", "error")
        sys.exit(1)

    # Фильтр лиц/текста
    use_face_filter = not args.no_face_filter
    use_text_filter = not args.no_text_filter

    stopped = False
    def stop_fn(): return stopped

    print(f"\n{'='*50}")
    print(f"Сайт:    {site}")
    print(f"Запрос:  {args.query}")
    print(f"Макс:    {args.max}")
    print(f"Цена:    {args.min_price}₽ — {'∞' if args.max_price == 0 else str(args.max_price) + '₽'}")
    print(f"Фильтр:  лица={'вкл' if use_face_filter else 'выкл'} текст={'вкл' if use_text_filter else 'выкл'}")
    print(f"{'='*50}\n")

    parser_obj = ParserCls(
        log_fn    = log,
        stop_fn   = stop_fn,
        delay     = args.delay,
        min_price = args.min_price,
        max_price = args.max_price,
    )

    saved   = 0
    skipped = 0

    try:
        for product in parser_obj.parse(args.query, args.max):
            # Фильтр фото
            if (use_face_filter or use_text_filter) and product.get("image_url"):
                try:
                    from face_filter import download_image, image_from_bytes, should_skip

                    img = None
                    if hasattr(parser_obj, "fetch_image_bytes"):
                        data = parser_obj.fetch_image_bytes(product["image_url"])
                        if data:
                            img = image_from_bytes(data)
                    if img is None:
                        img = download_image(product["image_url"])

                    if img is not None:
                        skip, reason = should_skip(
                            img,
                            check_faces=use_face_filter,
                            check_text=use_text_filter,
                        )
                        if skip:
                            log(f"🚫 пропуск ({reason}): {product['name'][:50]}", "warn")
                            skipped += 1
                            continue
                except Exception as fe:
                    log(f"face_filter error: {fe}", "dim")

            # Сохраняем в БД
            try:
                cur.execute("""
                    INSERT INTO products (ext_id, site, name, price, image_url, scraped_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (ext_id, site) DO UPDATE
                        SET name=EXCLUDED.name, price=EXCLUDED.price,
                            image_url=EXCLUDED.image_url, scraped_at=NOW()
                """, (product["ext_id"], product["site"], product["name"],
                      product["price"], product["image_url"]))
                saved += 1
                log(f"[{product['site']}] {product['name'][:55]}  — {product['price']:,}₽", "success")
            except Exception as e:
                log(f"DB error: {e}", "error")

    except KeyboardInterrupt:
        log("Остановлено пользователем", "warn")

    print(f"\n{'='*50}")
    print(f"Сохранено: {saved}")
    print(f"Пропущено: {skipped}")
    print(f"{'='*50}")

    conn.close()


if __name__ == "__main__":
    main()
