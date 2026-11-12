import pytest

from auth.repositories import UserRepository
from auth.schemas import UserCreate
from auth.models import User


@pytest.fixture
def repository(uow):
    return UserRepository(uow)


@pytest.fixture
def user_data():
    return UserCreate(
        email="test@example.com",
        username="testuser",
        password="password123",
        first_name="Test",
        last_name="User",
    )


@pytest.mark.asyncio
async def test_create_user(repository, user_data, session):
    user = await repository.create_user(user_data)

    assert isinstance(user, User)

    assert user.id is not None
    assert user.email == user_data.email
    assert user.username == user_data.username
    assert user.first_name == user_data.first_name
    assert user.last_name == user_data.last_name

    # Пароль не должен храниться в открытом виде
    assert user.hashed_password != user_data.password

    # Проверяем, что пароль действительно можно проверить
    from auth.repositories import ph

    assert ph.verify(
        user.hashed_password,
        user_data.password,
    )


@pytest.mark.asyncio
async def test_get_by_email(repository, user_data):
    user = await repository.create_user(user_data)

    result = await repository.get_by_email(user_data.email)

    assert result is not None
    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_by_email_not_found(repository):
    result = await repository.get_by_email("unknown@example.com")

    assert result is None


@pytest.mark.asyncio
async def test_get_by_username(repository, user_data):
    user = await repository.create_user(user_data)

    result = await repository.get_by_username(user_data.username)

    assert result is not None
    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_by_username_not_found(repository):
    result = await repository.get_by_username("unknown")

    assert result is None


@pytest.mark.asyncio
async def test_get_by_user_id(repository, user_data):
    user = await repository.create_user(user_data)

    result = await repository.get_by_user_id(user.id)

    assert result is not None
    assert result.email == user_data.email


@pytest.mark.asyncio
async def test_get_by_user_id_not_found(repository):
    result = await repository.get_by_user_id(999999)

    assert result is None


@pytest.mark.asyncio
async def test_check_user_exists(repository, user_data):
    user = await repository.create_user(user_data)

    result = await repository.check_user_exists(user.id)

    assert result is True


@pytest.mark.asyncio
async def test_check_user_not_exists(repository):
    result = await repository.check_user_exists(999999)

    assert result is False

