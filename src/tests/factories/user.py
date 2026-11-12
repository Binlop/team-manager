import pytest_asyncio
from auth.models import User


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