# MAX Mini App + FastAPI + PostgreSQL

Шаблон для хакатона: Mini App внутри мессенджера MAX, SvelteKit frontend, FastAPI backend и PostgreSQL.

## Что было изменено относительно исходного шаблона

Исходный проект был шаблоном Telegram WebApp: SvelteKit + FastAPI + MongoDB/Beanie/Motor + RabbitMQ + JWT. Это видно в исходной конфигурации и `README`, а также в исходных auth/db-модулях. Теперь активный runtime переведён на MAX Bridge и PostgreSQL/SQLAlchemy. Старые Telegram/RabbitMQ файлы оставлены как reference, но не подключаются новым `backend/main.py`.

### Новый стек

- **MAX Mini App / MAX Bridge** — окружение приложения внутри MAX.
- **SvelteKit + TypeScript** — UI.
- **FastAPI** — REST API.
- **PostgreSQL** — основная БД.
- **SQLAlchemy 2 async + asyncpg** — доступ к PostgreSQL.
- **MAX initData + HMAC-SHA256** — проверка личности пользователя.
- **JWT** — сессия после первичной авторизации.
- **Docker Compose** — локальный запуск.

Официальная документация MAX описывает MAX Bridge как библиотеку, предоставляющую `window.WebApp`, включая `initData` и `initDataUnsafe`; `initData` предназначен для серверной проверки, а `initDataUnsafe` нельзя использовать как доказательство личности. urlMAX Bridge documentationhttps://dev.max.ru/docs/webapps/bridge

## Быстрый запуск

### 1. Переменные окружения

```bash
cp .env.example .env
```

Заполни:

```env
MAX_BOT_TOKEN=...
SECRET_KEY=...
```

`MAX_BOT_TOKEN` — секрет бота MAX. Никогда не коммить его в Git.

### 2. Docker

```bash
docker compose up --build
```

После запуска:

```text
http://localhost:8000/          # frontend
http://localhost:8000/health    # healthcheck
http://localhost:8000/docs      # Swagger/OpenAPI
```

Для реального MAX Mini App нужен публичный HTTPS URL. Официальная документация MAX указывает, что Mini Apps работают внутри чат-ботов MAX и приложение должно быть размещено по HTTPS. urlMAX Mini Apps introductionhttps://dev.max.ru/docs/webapps/introduction

## Как работает авторизация

### Шаг 1 — MAX открывает frontend

`frontend/src/app.html` подключает MAX Bridge:

```html
<script src="https://st.max.ru/js/max-web-app.js"></script>
```

После этого доступен:

```js
window.WebApp
```

Frontend получает:

```js
WebApp.initData
```

### Шаг 2 — JS отправляет initData в FastAPI

```ts
await fetch("/api/user/auth", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ initData: WebApp.initData }),
});
```

### Шаг 3 — FastAPI проверяет подпись

Backend не доверяет `user.id`, который просто прислал браузер. Он получает подписанную строку `initData` и проверяет HMAC.

### Шаг 4 — PostgreSQL

После успешной проверки пользователь создаётся или обновляется в таблице `users`.

### Шаг 5 — JWT

Backend выдаёт access token. Все следующие защищённые запросы используют:

```http
Authorization: Bearer <token>
```

Полное объяснение находится в [`docs/BACKEND_GUIDE.md`](docs/BACKEND_GUIDE.md).

## API

### `POST /api/user/auth`

Body:

```json
{
  "initData": "auth_date=...&user=...&hash=..."
}
```

Response:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

### `GET /api/user/me`

Header:

```http
Authorization: Bearer eyJ...
```

Response:

```json
{
  "id": 123,
  "username": "example",
  "first_name": "Ivan",
  "last_name": "Ivanov",
  "language_code": "ru",
  "photo_url": "https://...",
  "is_staff": false
}
```

### `GET /health`

```json
{"status":"ok"}
```

## Как думать о FastAPI backend

Самая важная схема:

```text
JavaScript
   │ fetch()
   ▼
HTTP request
   │
   ▼
FastAPI router
   │
   ├── Pydantic validation
   ├── Depends(auth)
   └── endpoint
          │
          ▼
      SQLAlchemy
          │
          ▼
      PostgreSQL
          │
          ▼
      Python object
          │
          ▼
      JSON response
          │
          ▼
      JavaScript
```

Если ты понял эту цепочку, то уже понимаешь основу большинства современных web backend'ов.

## Где писать свою бизнес-логику

Не складывай всё в `main.py`.

Рекомендуемая структура для дальнейшей разработки:

```text
backend/
├── app/
│   ├── api/routes/        # HTTP endpoints
│   ├── schemas/            # Pydantic request/response DTO
│   └── services/           # бизнес-логика
├── bot/models.py           # SQLAlchemy models
└── core/
    ├── db.py
    ├── security.py
    └── env.py
```

Например:

```text
POST /api/orders
       ↓
orders.py
       ↓
OrderService.create_order()
       ↓
SQLAlchemy
       ↓
PostgreSQL
```

Так API остаётся тонким, а бизнес-логика не привязывается к HTTP.

## PostgreSQL vs MongoDB

Для хакатонного приложения я выбрал PostgreSQL.

Причины:

- пользователи, заказы, задачи, заявки и связи между сущностями естественно описываются таблицами;
- foreign keys защищают целостность данных;
- транзакции удобны для операций вида «создать заказ + записать событие»;
- SQL проще анализировать и отлаживать;
- PostgreSQL отлично подходит и для маленького MVP, и для дальнейшего роста.

MongoDB имеет смысл, если данные действительно документные и схема постоянно меняется. Для обычного Mini App backend PostgreSQL здесь практичнее.

## Что пока сознательно упрощено

1. Таблицы создаются через `Base.metadata.create_all()` при старте. Для production нужен Alembic.
2. JWT хранится в `localStorage` для простоты демо. Для более строгого production-сценария можно использовать возможности `SecureStorage` MAX Bridge.
3. Нет rate limiting.
4. Нет полноценного слоя service/repository — для хакатонного MVP это избыточно, его стоит добавить при росте логики.
5. Старые Telegram/RabbitMQ файлы не удалены, чтобы можно было сравнить архитектуры и миграцию.

## Важная безопасность

Никогда не делай так:

```ts
fetch("/api/user/me?user_id=" + user.id)
```

и не доверяй `user_id` из браузера.

Правильная модель:

```text
MAX → signed initData → backend validates signature
                              ↓
                         trusted user id
                              ↓
                         PostgreSQL
```

Также никогда не публикуй `MAX_BOT_TOKEN` или `SECRET_KEY` в GitHub.

## Следующий шаг для хакатона

Поверх этого каркаса можно сразу добавлять доменную модель проекта:

```text
User
 ├── Profile
 ├── Tasks / Orders
 ├── Actions
 └── Notifications
```

Для каждой сущности делаем:

```text
SQLAlchemy model
      ↓
Pydantic schemas
      ↓
FastAPI router
      ↓
service/business logic
      ↓
frontend fetch()
      ↓
Svelte UI
```

Именно этот цикл стоит освоить: после него добавление новых экранов и функций превращается в повторение одной и той же понятной схемы.

## License

MIT.
