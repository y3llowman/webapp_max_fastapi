# Как работает этот backend

## 1. Архитектура

```text
MAX Client
   │
   │ HTTPS + MAX Bridge
   ▼
SvelteKit frontend
   │
   │ POST /api/user/auth
   │ { initData }
   ▼
FastAPI
   │
   ├── validate_max_init_data()
   │       └── HMAC-SHA256 → доверяем личности только после проверки
   │
   ├── PostgreSQL / SQLAlchemy
   │       └── users
   │
   └── JWT access token
           │
           ▼
   GET /api/user/me
   Authorization: Bearer <JWT>
```

Исходный шаблон был Telegram WebApp + FastAPI + MongoDB + RabbitMQ. В нём frontend отправлял `initData` и `initDataUnsafe` на `/api/user/auth`, а backend проверял Telegram-подпись и создавал JWT. MongoDB подключалась через Beanie/Motor. Теперь эта схема заменена на MAX Bridge + PostgreSQL + SQLAlchemy. См. исходную структуру проекта и исходную реализацию auth в `backend/app/api/routes/users.py`, `backend/core/db.py` и `backend/bot/models.py`.

## 2. Что происходит после открытия Mini App

MAX загружает статические HTML/CSS/JS-файлы. Подключён официальный MAX Bridge:

```html
<script src="https://st.max.ru/js/max-web-app.js"></script>
```

После загрузки появляется `window.WebApp`. Из него frontend берёт `WebApp.initData`. В отличие от `initDataUnsafe`, `initData` предназначен для серверной проверки и содержит подписанные стартовые параметры.

### Frontend → FastAPI

```ts
const response = await fetch("/api/user/auth", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ initData: WebApp.initData }),
});
```

HTTP здесь можно понимать буквально:

1. браузер/встроенный WebView создаёт TCP/TLS-соединение с сервером;
2. отправляет `POST /api/user/auth`;
3. FastAPI получает HTTP request;
4. Pydantic превращает JSON body в `AuthRequest`;
5. endpoint вызывает `validate_max_init_data()`;
6. после успешной проверки backend находит или создаёт пользователя в PostgreSQL;
7. backend возвращает JSON с JWT.

## 3. Почему нельзя отправлять только user_id

Плохой вариант:

```json
POST /api/user/auth
{"user_id": 123}
```

Любой человек может открыть DevTools и заменить `123` на чужой ID.

Правильный вариант:

```json
POST /api/user/auth
{"initData": "auth_date=...&user=...&hash=..."}
```

Backend знает секрет бота, вычисляет подпись самостоятельно и сравнивает её с `hash`. Если данные изменены, подпись перестаёт совпадать.

Важно: `initDataUnsafe` можно использовать для UI, но нельзя использовать как доказательство личности пользователя.

## 4. HMAC-проверка

В упрощённом виде:

```text
MAX WebApp
    │
    ├── user
    ├── auth_date
    ├── query_id
    └── hash = HMAC(secret, data)
             │
             ▼
        HTTPS POST
             │
             ▼
FastAPI получает initData
             │
             ├── удаляет hash
             ├── сортирует остальные key=value
             ├── строит data_check_string
             ├── вычисляет HMAC своим секретом
             └── compare_digest(calculated, received)
```

После этого сервер может безопасно извлечь `user.id`.

## 5. Зачем JWT после initData

`initData` нужен для первичной идентификации через MAX. Необязательно отправлять его на каждый API-запрос.

После успешной авторизации сервер выдаёт JWT:

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

Дальше frontend делает:

```http
GET /api/user/me
Authorization: Bearer eyJ...
```

FastAPI dependency `get_current_user()`:

1. достаёт Bearer token;
2. проверяет JWT подпись;
3. получает `sub` = MAX user ID;
4. ищет пользователя в PostgreSQL;
5. передаёт объект `User` endpoint'у.

Это и есть dependency injection FastAPI.

## 6. PostgreSQL

Используется SQLAlchemy 2.x в async-режиме и драйвер `asyncpg`.

```python
engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(engine)
```

Каждый запрос получает свою async session:

```python
async def get_db():
    async with SessionLocal() as session:
        yield session
```

Модель `User` описывает таблицу `users`. SQLAlchemy переводит Python-описание в SQL.

Для хакатона таблицы создаются при startup через `Base.metadata.create_all`. Для production лучше заменить это на Alembic migrations.

## 7. Что такое endpoint

```python
@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return user
```

Декоратор говорит FastAPI:

> если пришёл GET на `/api/user/me`, вызови эту функцию.

`Depends(get_current_user)` означает:

> прежде чем вызвать `get_me`, выполни `get_current_user` и передай его результат в аргумент `user`.

## 8. JSON и Pydantic

Frontend отправляет:

```json
{"initData":"..."}
```

Pydantic-модель:

```python
class AuthRequest(BaseModel):
    initData: str
```

FastAPI автоматически:

- читает JSON;
- валидирует типы;
- создаёт `AuthRequest`;
- отдаёт 422, если body не соответствует схеме.

Поэтому тебе не нужно вручную писать `request.json()` для каждого endpoint.

## 9. Почему async

FastAPI может обслуживать много одновременных соединений. Когда запрос ждёт PostgreSQL, coroutine отдаёт управление event loop вместо блокировки всего процесса.

Упрощённо:

```text
request A → PostgreSQL ───────────────┐
request B → обработка                   │
request C → PostgreSQL ────────┐       │
request D → обработка          │       │
                                ▼       ▼
                           ответы A/C
```

Именно поэтому используются `async def`, `AsyncSession` и `asyncpg`.

## 10. Структура проекта

```text
backend/
├── main.py                  # создание FastAPI приложения
├── app/api/
│   ├── depends.py           # auth dependencies
│   └── routes/
│       ├── main.py          # сборка API router
│       └── users.py         # /api/user/*
├── bot/
│   └── models.py            # SQLAlchemy models
└── core/
    ├── config.py            # настройки приложения
    ├── env.py               # .env → Pydantic Settings
    ├── db.py                # PostgreSQL engine/session
    └── security.py          # MAX HMAC + JWT

frontend/src/
├── lib/max.ts               # адаптер MAX Bridge
├── services/api.ts          # HTTP requests к FastAPI
└── routes/+page.svelte      # Mini App UI
```

Старые Telegram/RabbitMQ-файлы пока оставлены в репозитории для удобства сравнения, но новый entrypoint их не подключает. Их можно удалить отдельным cleanup-коммитом после проверки хакатонного сценария.

## 11. Как добавить новый API endpoint

Например, список задач:

```python
@router.get("/tasks")
async def get_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Task).where(Task.owner_id == user.id))
    return result.scalars().all()
```

Frontend:

```ts
const token = localStorage.getItem("max_access_token");
const response = await fetch("/api/tasks", {
  headers: { Authorization: `Bearer ${token}` },
});
const tasks = await response.json();
```

Получается стандартный цикл:

```text
Svelte component
      ↓
fetch()
      ↓
HTTP/JSON
      ↓
FastAPI router
      ↓
Depends(auth)
      ↓
SQLAlchemy
      ↓
PostgreSQL
      ↓
Pydantic/JSON
      ↓
fetch().json()
      ↓
Svelte state
      ↓
UI
```

## 12. Что делать перед production

- заменить `create_all` на Alembic;
- сделать отдельного database user с минимальными правами;
- хранить `MAX_BOT_TOKEN` и `SECRET_KEY` только в secret storage;
- включить HTTPS;
- уменьшить `MAX_INIT_DATA_MAX_AGE` до рекомендованного значения;
- не доверять данным из frontend без серверной проверки;
- добавить rate limiting;
- добавить структурированные логи;
- добавить тесты HMAC/auth и API;
- при росте нагрузки использовать несколько worker processes и внешний reverse proxy;
- JWT лучше хранить в более защищённом хранилище MAX Bridge, если сценарий и версия клиента это позволяют, вместо обычного localStorage.
