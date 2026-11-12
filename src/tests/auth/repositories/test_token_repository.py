import pytest
import pytest_asyncio

from datetime import datetime, timedelta, timezone

from auth.repositories import TokenRepository
from auth.models import Token
from auth.schemas import UserCreate
from auth.repositories import UserRepository


@pytest.fixture
def repository(uow):
    return TokenRepository(uow)


@pytest.fixture
def user_data():
    return UserCreate(
        email="test@example.com",
        username="testuser",
        password="password123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def expires_at():
    return datetime.now(timezone.utc) + timedelta(days=30)


@pytest_asyncio.fixture
async def user(uow, user_data):
    repository = UserRepository(uow)
    return await repository.create_user(user_data)


@pytest.mark.asyncio
async def test_save_refresh_token(repository, user, expires_at):
    token = await repository.save_refresh_token(
        jti="test-jti",
        user_id=user.id,
        expires_at=expires_at,
    )

    assert isinstance(token, Token)
    assert token.jti == "test-jti"
    assert token.user_id == user.id
    assert token.expires_at == expires_at


@pytest.mark.asyncio
async def test_get_token_by_jti(repository, user, expires_at):
    token = await repository.save_refresh_token(
        jti="test-jti",
        user_id=user.id,
        expires_at=expires_at,
    )

    result = await repository.get_token_by_jti("test-jti")

    assert result is not None
    assert result.id == token.id
    assert result.jti == "test-jti"


@pytest.mark.asyncio
async def test_get_token_by_jti_not_found(repository):
    result = await repository.get_token_by_jti("unknown-jti")

    assert result is None


@pytest.mark.asyncio
async def test_revoke_token(repository, user, expires_at):
    token = await repository.save_refresh_token(
        jti="test-jti",
        user_id=user.id,
        expires_at=expires_at,
    )

    await repository.revoke_token(token)

    assert token.revoked is True
    assert token.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_token_by_jti(repository, user, expires_at):
    token = await repository.save_refresh_token(
        jti="test-jti",
        user_id=user.id,
        expires_at=expires_at,
    )

    await repository.revoke_token_by_jti("test-jti")

    result = await repository.get_token_by_jti("test-jti")

    assert result.revoked is True
    assert result.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_all_for_user(repository, user, expires_at):
    token1 = await repository.save_refresh_token(
        jti="jti-1",
        user_id=user.id,
        expires_at=expires_at,
    )

    token2 = await repository.save_refresh_token(
        jti="jti-2",
        user_id=user.id,
        expires_at=expires_at,
    )

    await repository.revoke_all_for_user(user.id)

    result1 = await repository.get_token_by_jti("jti-1")
    result2 = await repository.get_token_by_jti("jti-2")

    assert result1.revoked is True
    assert result2.revoked is True

    assert result1.revoked_at is not None
    assert result2.revoked_at is not None

@pytest.mark.asyncio
async def test_revoke_all_for_user_does_not_affect_other_users(
    repository,
    uow,
    user,
    expires_at,
):
    another_user = await UserRepository(uow).create_user(
        UserCreate(
            email="another@example.com",
            username="another",
            password="password123",
            first_name="Another",
            last_name="User",
        )
    )

    await repository.save_refresh_token(
        jti="user-1-token",
        user_id=user.id,
        expires_at=expires_at,
    )

    await repository.save_refresh_token(
        jti="user-2-token",
        user_id=another_user.id,
        expires_at=expires_at,
    )

    await repository.revoke_all_for_user(user.id)

    token1 = await repository.get_token_by_jti("user-1-token")
    token2 = await repository.get_token_by_jti("user-2-token")

    assert token1.revoked is True
    assert token2.revoked is False