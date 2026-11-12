import pytest
import pytest_asyncio
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
import db.models
from db.session import Base
from db.uow import UnitOfWork
from auth.models import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    
@pytest_asyncio.fixture(loop_scope="session")
async def session(engine):
    async with engine.connect() as conn:
        trans = await conn.begin()
        async_session = async_sessionmaker(
            bind=conn,
            class_=AsyncSession,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with async_session() as session:
            yield session
        await trans.rollback()

@pytest.fixture()
def uow(session):
    return UnitOfWork(session)


@pytest_asyncio.fixture
async def user_factory(uow):
    async def create_user(
        *,
        username: str = "testuser",
        email: str = "test@example.com",
        hashed_password: str = "hashed_password",
        is_active: bool = True,
    ) -> User:
        user = User(
            username=username,
            email=email,
            hashed_password=hashed_password,
            is_active=is_active,
        )

        uow.db.add(user)
        await uow.db.flush()

        return user

    return create_user

@pytest_asyncio.fixture
async def user(user_factory):
    return await user_factory()


@pytest_asyncio.fixture
async def user2(user_factory):
    return await user_factory(
        username="user2",
        email="user2@example.com",
    )

async def detach_all(session) -> None:
    """
    Сбрасывает identity map, чтобы репозиторий загрузил объекты заново.
    Так мы проверяем, что joinedload/selectinload действительно подгрузили
    связи: в async-сессии ленивая загрузка бросила бы MissingGreenlet.
    """
    await session.flush()
    session.expunge_all()