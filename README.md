# Price Guesser — Deploy

## Структура

```
deploy/
├── docker-compose.yml
├── .env                  ← создать из .env.example
├── backend/
│   ├── Dockerfile
│   ├── main.py           ← скопировать из price_guesser/backend/
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── next.config.js    ← важно! использовать версию из deploy/
│   └── ...все файлы Next.js (app/, lib/, package.json и т.д.)
└── parser/
    ├── Dockerfile
    ├── run.py            ← CLI запуск парсера
    ├── requirements.txt
    ├── face_filter.py    ← скопировать
    ├── db.py             ← скопировать
    └── parsers/          ← скопировать всю папку
        ├── __init__.py
        ├── base.py
        ├── wildberries.py
        ├── ozon.py
        ├── lamoda.py
        └── tsum.py
```

## Запуск

```bash
# 1. Настрой пароль
cp .env.example .env
nano .env

# 2. Собери и запусти
docker compose up -d --build

# 3. Проверь
docker compose ps
```

## Сайт

- Игра:    http://your-server:3000
- API:     http://your-server:8000/docs

## Запуск парсера через Portainer

1. Открой Portainer → Containers → parser
2. Нажми **>_ Console** → Connect
3. Введи команду:

```bash
python run.py --site wildberries --query кроссовки --max 100
python run.py --site lamoda --query кроссовки --max 100
python run.py --site tsum --query кроссовки --max 50
python run.py --list   # список сайтов
```

## Обновление

```bash
docker compose down
docker compose up -d --build
```
