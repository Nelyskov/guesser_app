# Price Guesser — Game

Игра "Угадай цену" с двумя режимами.

## Структура

```
price_guesser/
├── backend/          # FastAPI
│   ├── main.py
│   └── requirements.txt
└── frontend/         # Next.js
    ├── app/
    │   ├── page.tsx          # Главная
    │   ├── slider/page.tsx   # Режим "Угадай цену"
    │   ├── higher/page.tsx   # Режим "Что дороже"
    │   └── leaderboard/      # Таблица лидеров
    └── lib/api.ts
```

## Запуск

### 1. Backend (FastAPI)

```bash
cd backend
pip install -r requirements.txt

# Настрой переменные БД (или оставь дефолтные)
# DB_HOST=localhost DB_PORT=5432 DB_NAME=price_guesser
# DB_USER=postgres DB_PASSWORD=password

uvicorn main:app --reload --port 8000
```

API доступен на http://localhost:8000
Документация: http://localhost:8000/docs

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

Сайт на http://localhost:3000

---

## Переменные окружения для backend

Создай файл `backend/.env`:

```
DB_HOST=localhost
DB_PORT=5432
DB_NAME=price_guesser
DB_USER=postgres
DB_PASSWORD=password
```
