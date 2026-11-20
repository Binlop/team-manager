# NEW: Интеграционные happy-path тесты домена auth.
# Реальные репозитории + сервисы + БД (SQLite in-memory через src/tests/conftest.py).
# Сценарий: register -> login -> refresh_token -> logout.

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from auth.repositories import TokenRepository, UserRepository
from auth.schemas import RefreshTokenRequest, UserCreate, UserLogin
from auth.services import TokenService, UserService
from core.security import verify_token


@pytest_asyncio.fixture
async def user_repository(uow):
    return UserRepository(uow)


@pytest_asyncio.fixture
async def token_repository(uow):
    return TokenRepository(uow)


@pytest.fixture
def cache():
    return AsyncMock()


@pytest_asyncio.fixture
async def user_service(user_repository, token_repository, cache):
    return UserService(
        user_repository=user_repository,
        token_repository=token_repository,
        cache=cache,
    )


@pytest_asyncio.fixture
async def token_service(uow):
    return TokenService(uow)


async def _register_new_user(user_service, email: str = "happy@example.com", username: str = "happyuser"):
    return await user_service.register(
        UserCreate(
            email=email,
            username=username,
            password="password123",
            first_name="Happy",
            last_name="User",
        )
    )


# NEW: happy path — регистрация, логин, сохранение refresh-токена в БД
@pytest.mark.asyncio
async def test_auth_happy_path_register_and_login(user_service, token_repository):
    user = await _register_new_user(user_service)
    assert user.id is not None

    tokens = await user_service.login(
        UserLogin(identifier="happyuser", password="password123")
    )

    access_payload = verify_token(tokens.access_token, expected_type="access")
    refresh_payload = verify_token(tokens.refresh_token, expected_type="refresh")

    assert access_payload["sub"] == str(user.id)
    assert refresh_payload["sub"] == str(user.id)

    stored_token = await token_repository.get_token_by_jti(refresh_payload["jti"])
    assert stored_token is not None
    assert stored_token.user_id == user.id
    assert stored_token.revoked is False
    assert stored_token.expires_at is not None


# NEW: happy path — обмен refresh-токена (ротация)
# @pytest.mark.xfail(
#     reason=(
#         "Баг: TokenService.update_refresh_token сравнивает token.expires_at "
#         "(может быть offset-naive после SQLite) с datetime.now(timezone.utc) (aware) "
#         "бросает TypeError."
#     ),
#     strict=False,
# )
@pytest.mark.asyncio
async def test_auth_happy_path_refresh_token(user_service, token_service):
    user = await _register_new_user(user_service)
    tokens = await user_service.login(
        UserLogin(identifier="happyuser", password="password123")
    )
    old_jti = verify_token(tokens.refresh_token, expected_type="refresh")["jti"]

    new_tokens = await token_service.update_refresh_token(
        RefreshTokenRequest(refresh_token=tokens.refresh_token)
    )
    new_refresh_payload = verify_token(new_tokens.refresh_token, expected_type="refresh")

    old_token = await token_service.token_repository.get_token_by_jti(old_jti)
    assert old_token is not None
    assert old_token.revoked is True

    new_token = await token_service.token_repository.get_token_by_jti(new_refresh_payload["jti"])
    assert new_token is not None
    assert new_token.revoked is False


# NEW: happy path — logout (revoke refresh-токена)
@pytest.mark.asyncio
async def test_auth_happy_path_logout(user_service, token_repository):
    user = await _register_new_user(user_service)
    tokens = await user_service.login(
        UserLogin(identifier="happyuser", password="password123")
    )
    refresh_payload = verify_token(tokens.refresh_token, expected_type="refresh")

    await user_service.logout(RefreshTokenRequest(refresh_token=tokens.refresh_token))

    stored_token = await token_repository.get_token_by_jti(refresh_payload["jti"])
    assert stored_token is not None
    assert stored_token.revoked is True
