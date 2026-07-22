# Price Guesser · Parser

Парсер товаров с GUI для сбора данных (название, цена, изображение)  
в PostgreSQL. Поддерживаемые сайты: **Wildberries, Ozon, Lamoda, ЦУМ**.

---

## Установка

```bash
cd parser_app
pip install -r requirements.txt
```

Если нет tkinter (Linux):
```bash
sudo apt install python3-tk
```

---

## Запуск

```bash
python main.py
```

---

## PostgreSQL

Создай базу данных перед запуском:

```sql
CREATE DATABASE price_guesser;
```

Схема создаётся автоматически при первом подключении через кнопку  
**«Подключить БД»**.

Таблица `products`:

| Колонка    | Тип       | Описание                        |
|------------|-----------|---------------------------------|
| id         | SERIAL    | Внутренний ID                   |
| ext_id     | TEXT      | ID товара на сайте              |
| site       | TEXT      | Wildberries / Ozon / Lamoda / ЦУМ |
| name       | TEXT      | Название товара                 |
| price      | INTEGER   | Цена в рублях                   |
| image_url  | TEXT      | Прямая ссылка на фото           |
| scraped_at | TIMESTAMP | Время парсинга                  |

---

## Структура проекта

```
parser_app/
├── main.py              # GUI (tkinter)
├── db.py                # PostgreSQL-слой
├── requirements.txt
├── parsers/
│   ├── base.py          # Базовый класс
│   ├── wildberries.py   # WB JSON API
│   ├── ozon.py          # Ozon internal API
│   ├── lamoda.py        # Lamoda API + HTML fallback
│   └── tsum.py          # ЦУМ API + Next.js SSR + BS4
```

---

## Примечания

- **Wildberries** — использует публичный JSON API, работает стабильно.
- **Ozon** — использует внутренний API (`composer-api.bx`), требует  
  прогрева сессии; структура ответа может меняться.
- **Lamoda** — пробует JSON API, при неудаче парсит HTML  
  через `__PRELOADED_STATE__`.
- **ЦУМ** — пробует JSON API, затем `__NEXT_DATA__` (Next.js),  
  затем BeautifulSoup.

Если сайт изменил структуру — скинь HTML страницы, обновим парсер.

---

## Для игры «Угадай цену»

После парсинга запроси данные из БД:

```python
import psycopg2, random

conn = psycopg2.connect(...)
cur  = conn.cursor()
cur.execute("SELECT id, name, price, image_url FROM products ORDER BY RANDOM() LIMIT 1")
product = cur.fetchone()
```
