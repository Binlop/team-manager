"""
Общие фикстуры для API-интеграционных тестов (TestClient + реальная БД).

- БД: SQLite in-memory (aiosqlite) с StaticPool — одна общая БД на сессию.
- get_uow переопределяется на тестовый UnitOfWork, чтобы эндпоинты работали
  против реальной БД, а не моков.
- Auth: реальный JWT-флоу (register -> login -> me / refresh / logout).
"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import db.models
from db.session import Base
from db.uow import UnitOfWork
from db.uow import get_uow as real_get_uow

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
)
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    class_=AsyncSession,
    bind=async_engine,
    expire_on_commit=False,
)


async def _init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


asyncio.run(_init_db())


async def _override_get_uow():
    async with AsyncSessionLocal() as session:
        async with UnitOfWork(session) as uow:
            yield uow


@pytest.fixture
def override_get_uow():
    return _override_get_uow


@pytest.fixture
def client(override_get_uow):
    from main import app

    app.dependency_overrides[real_get_uow] = override_get_uow
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
