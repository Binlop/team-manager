# Team Manager API

REST API для управления командой: создание команд, приглашения участников, задачи с оценками и встречи.

## Содержание

- [Стек и требования](#стек-и-требования)
- [Quick start](#quick-start)
- [Переменные окружения (.env)](#переменные-окружения-env)
- [Миграции](#миграции)
- [Auth: как начать пользоваться API](#auth-как-начать-пользоваться-api)
- [Тесты](#тесты)
- [Структура проекта](#структура-проекта)
- [API-реестр](#api-реестр)
- [Ограничения](#ограничения)

## Стек и требования

- Python **>= 3.14**
- FastAPI / Starlette / Pydantic v2
- SQLAlchemy 2.x (async, asyncpg) + Alembic
- PostgreSQL
- Redis (cache / refresh tokens через `app.state.redis`)
- Auth: python-jose (JWT) + argon2
- Логирование: structlog
- Тесты: pytest, pytest-asyncio, testcontainers (PostgreSQL), httpx (TestClient)

Требования к окружению: Python 3.14+, `uv`, PostgreSQL локально и наличие тестовой базы данных (team_manager), Redis.

## Quick start

```bash
# 1. Установка зависимостей
uv sync

# 2. Настройка окружения (.env — скопировать из .env.example)
cp src/core/.env.example src/core/.env   # либо создать .env рядом с src/core/.env

# 3. Применение миграций
uv run alembic -c src/alembic.ini upgrade head

# 4. Запуск
uv run --env-file .env.uv fastapi dev src/main.py
```

Приложение читает настройки из `src/core/.env` (или `src/core/.env.example`, если `.env` отсутствует).

## Переменные окружения (.env)

| Переменная | Описание | По умолчанию |
|---|---|---|
| `SECRET_KEY` | Секрет для подписи JWT (**обязательный**) | — |
| `DEBUG` | Режим отладки FastAPI (`/docs` включены) | `False` |
| `APP_ENV` | `prod` / `dev` / `test` | `dev` |
| `PROJECT_NAME` | Название приложения | `Team Manager API` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | TTL access-токена | `30` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | TTL refresh-токена | `7` |
| `REFRESH_COOKIE` / `REFRESH_COOKIE_PATH` | Параметры refresh-cookie | `refresh_token` / `/api/v1/auth` |
| `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`, `DB_HOST` | Параметры PostgreSQL | `postgres` / `postgres` / `team_manager` / `5432` / `127.0.0.1` |
| `REDIS_PORT`, `REDIS_DB`, `REDIS_URL_CACHE`, `REDIS_URL_CELERY` | Параметры Redis | `6379` / `0` / ... |

## Миграции

```bash
# создание новой миграции
uv run alembic -c src/alembic.ini revision --autogenerate -m "<комментарий>"

# применение миграций
uv run alembic -c src/alembic.ini upgrade head
```

## Auth: как начать пользоваться API

1. `POST /api/v1/auth/register` — регистрация (`UserCreate`: username, email, password, first_name, last_name) → `201 UserRead`.
2. `POST /api/v1/auth/login` — вход (`UserLogin`: identifier (username или email) + password) → `200 TokenResponse` (access + refresh).
3. Доступ к защищённым эндпоинтам — header `Authorization: Bearer <access_token>`.

Дополнительно:
- `POST /api/v1/auth/token` — OAuth2 password flow (form: `username`/`password`).
- `POST /api/v1/auth/refresh_token` — ротация refresh-токена (`refresh_token` query param) → новые токены.
- `POST /api/v1/auth/logout` — отзыв refresh-токена (`refresh_token` query param) → `204`.
- `GET /api/v1/auth/me` — текущий пользователь (`UserDep`) → username.

## Тесты

```bash
# все тесты
uv run pytest

# только API/интеграционные тесты
uv run pytest src/tests/api

# с покрытием
uv run pytest --cov --cov-report=term-missing
```

Тесты используют:
- юнит-тесты сервисов/репозиториев — моки + savepoint-rollback;
- интеграционные тесты — `TestClient` + реальная БД (SQLite in-memory / testcontainers PostgreSQL).

## Структура проекта

```
src/
├── main.py            # FastAPI app, lifespan, регистрация обработчиков
├── middleware.py      # AccessLogMiddleware (чистый ASGI)
├── api/
│   └── v1/            # HTTP-слой
│       ├── router.py  # объединение роутеров (/api/v1/...)
│       ├── auth.py    # /auth/*
│       ├── team.py    # /team/*, /meeting/*
│       ├── task.py    # /tasks/*, /comments/*
│       └── agenda.py  # /calendar/*
├── core/              # config, security, exceptions, logging, cache, lifespan, exception_handlers
├── db/                # session, models, uow (Unit of Work)
└── apps/              # бизнес-логика по доменам
    ├── auth/          # models, schemas, repos, services, exceptions, deps
    ├── teams/         # Team, TeamMember, Meeting, UserMeeting
    ├── tasks/         # Task, Comment, TaskStatus
    └── agenda/        # CalendarRead
└── tests/             # тесты (unit + integration + API)
└── migrations/        # alembic
```

Слои:

- **api/v1** — FastAPI роутеры, привязка `ServiceDep` и `UserDep`.
- **apps/<domain>** — сервисы (Use Case), исключения домана, схемы, репозитории.
- **db** — SQLAlchemy session, `UnitOfWork` (commit/rollback), модели.
- **core** — конфиг, JWT, обработчики ошибок (DomainError → JSON), middleware, логгер.

## API-реестр

### Auth (`/api/v1/auth`)

| Метод | Путь | Право | Описание |
|---|---|---|---|
| POST | `/api/v1/auth/register` | public | Регистрация → 201 |
| POST | `/api/v1/auth/login` | public | Логин → 200 (tokens) |
| POST | `/api/v1/auth/token` | public | OAuth2 login (form) → 200 |
| POST | `/api/v1/auth/logout` | public | Отзыв refresh (`refresh_token` query) → 204 |
| POST | `/api/v1/auth/refresh_token` | public | Ротация refresh (`refresh_token` query) → 200 |
| GET | `/api/v1/auth/me` | auth | Текущий пользователь → 200 |

### Teams (`/api/v1/team`)

| Метод | Путь | Право | Описание |
|---|---|---|---|
| POST | `/api/v1/team/` | auth | Создать команду → 201 (с invite_code) |
| GET | `/api/v1/team/{team_id}` | auth | Получить команду (участник/менеджер) → 200 / 404 |
| GET | `/api/v1/team/{team_id}/join/{invite_code}` | auth | Join по invite-коду → 200 |
| GET | `/api/v1/team/{team_id}/members` | auth | Список участников → 200 / 404 |
| PUT | `/api/v1/team/{team_id}` | auth (manager) | Обновить команду → 200 / 403 |
| PUT | `/api/v1/team/{team_id}/refresh-invite-code` | auth (manager) | Обновить invite-код → 200 |
| POST | `/api/v1/team/{team_id}/member` | auth (manager) | Добавить участника → 201 |
| PUT | `/api/v1/team/{team_id}/member` | auth (manager) | Сменить роль → 200 |
| DELETE | `/api/v1/team/{team_id}/member` | auth (manager) | Удалить участника (`user_id` query) → 204 |

### Meetings (`/api/v1/meeting`)

| Метод | Путь | Право | Описание |
|---|---|---|---|
| POST | `/api/v1/meeting/` | auth | Создать встречу → 201 |
| POST | `/api/v1/meeting/add-participant` | auth | Добавить участника в встречу → 201 |
| GET | `/api/v1/meeting/my-meetings` | auth | Мои встречи → 200 |
| PUT | `/api/v1/meeting/{meeting_id}` | auth (organizer) | Обновить встречу → 200 |
| DELETE | `/api/v1/meeting/{meeting_id}` | auth (organizer) | Удалить встречу → 204 |

### Tasks (`/api/v1/tasks)

| Метод | Путь | Право | Описание |
|---|---|---|---|
| GET | `/api/v1/tasks/my-tasks` | auth | Мои задачи → 200 |
| GET | `/api/v1/tasks/mean-score` | auth | Средняя оценка → 200 |
| POST | `/api/v1/tasks/` | auth (manager) | Создать задачу → 201 |
| GET | `/api/v1/tasks/{task_id}` | auth (assignee/member/manager) | Получить задачу → 200 / 404 |
| PUT | `/api/v1/tasks/{task_id}` | auth (manager) | Обновить задачу (status/score/…) → 200 / 403 / 409 |
| GET | `/api/v1/tasks/team-tasks/{team_id}` | auth | Задачи команды → 200 / 404 |
| DELETE | `/api/v1/tasks/{task_id}` | auth (assignee/manager) | Удалить задачу → 204 / 403 |
| GET | `/api/v1/tasks/{task_id}/comments` | auth | Комментарии задачи → 200 / 404 |
| POST | `/api/v1/tasks/comments/` | auth | Создать комментарий → 201 |
| GET | `/api/v1/tasks/comments/{comment_id}` | auth (author) | Получить комментарий → 200 / 404 |
| PUT | `/api/v1/tasks/comments/{comment_id}` | auth (author) | Обновить комментарий → 200 / 404 |
| DELETE | `/api/v1/tasks/comments/{comment_id}` | auth (author) | Удалить комментарий → 204 / 404 |

### Calendar (`/api/v1/calendar`)

| Метод | Путь | Право | Описание |
|---|---|---|---|
| GET | `/api/v1/calendar` | auth | События на окно (meetings/tasks) → 200 |

## Ограничения

- Не реализовано: refresh-token хранится в Redis cache + БД - ротация, celery-фоновые задачи.
- Заготовка `PaginationDep` (`api/deps.py`) есть, но не подключена ко всем эндпоинтам.
- Текущая модель прав: менеджер команды — полный доступ; участник — только свои задачи/встречи.
- `GET /api/v1/auth/me` возвращает username без `response_model` (сырая строка).
