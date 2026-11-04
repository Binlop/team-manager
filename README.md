
### Запуск приложения

```bash
uv run --env-file .env fastapi dev src/main.py
```

### Создание миграции

```bash
uv run --env-file .env alembic -c src/alembic.ini revision --autogenerate -m "<комментарий>"
```

### Применение миграций

```bash
uv run --env-file .env alembic -c src/alembic.ini upgrade head
```