import pytest
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from unittest.mock import AsyncMock, MagicMock, patch
from types import SimpleNamespace

from auth.services import UserService
from auth.schemas import UserCreate, UserLogin, RefreshTokenRequest
from auth.exceptions import (
    UserNotFoundError,
    InvalidCredentialsError,
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
    UserAlreadyDeletedError,
    InvalidTokenError,
)


@pytest.fixture
def user_repository():
    return AsyncMock()


@pytest.fixture
def token_repository():
    return AsyncMock()


@pytest.fixture
def cache():
    return AsyncMock()


@pytest.fixture
def service(user_repository, token_repository, cache):
    return UserService(
        user_repository=user_repository,
        token_repository=token_repository,
        cache=cache,
    )


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
def user():
    return SimpleNamespace(
        id=1,
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password",
        is_active=True,
    )


# =========================
# REGISTER
# =========================

@pytest.mark.asyncio
async def test_register(service, user_repository, user_data, user):
    user_repository.get_by_email.return_value = None
    user_repository.get_by_username.return_value = None
    user_repository.create_user.return_value = user

    result = await service.register(user_data)

    assert result == user

    user_repository.get_by_email.assert_awaited_once_with(
        user_data.email
    )

    user_repository.get_by_username.assert_awaited_once_with(
        user_data.username
    )

    user_repository.create_user.assert_awaited_once_with(
        user_data
    )


@pytest.mark.asyncio
async def test_register_email_already_exists(
    service,
    user_repository,
    user_data,
    user,
):
    user_repository.get_by_email.return_value = user

    with pytest.raises(EmailAlreadyExistsError):
        await service.register(user_data)

    user_repository.get_by_email.assert_awaited_once_with(
        user_data.email
    )

    user_repository.get_by_username.assert_not_awaited()
    user_repository.create_user.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_username_already_exists(
    service,
    user_repository,
    user_data,
    user,
):
    user_repository.get_by_email.return_value = None
    user_repository.get_by_username.return_value = user

    with pytest.raises(UsernameAlreadyExistsError):
        await service.register(user_data)

    user_repository.get_by_email.assert_awaited_once_with(
        user_data.email
    )

    user_repository.get_by_username.assert_awaited_once_with(
        user_data.username
    )

    user_repository.create_user.assert_not_awaited()


# =========================
# LOGIN
# =========================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "identifier, lookup_method",
    [
        ("test@example.com", "get_by_email"),
        ("testuser", "get_by_username"),
    ],
)
async def test_login(
    service,
    user_repository,
    token_repository,
    user,
    identifier,
    lookup_method,
):
    getattr(user_repository, lookup_method).return_value = user
    with (
        patch.object(PasswordHasher, "verify", return_value=True),
        patch(
            "auth.services.create_access_token",
            return_value="access-token",
        ),
        patch(
            "auth.services.create_refresh_token",
            return_value=(
                "refresh-token",
                "test-jti",
                MagicMock(),
            ),
        ),
    ):
        result = await service.login(
            UserLogin(
                identifier=identifier,
                password="password123",
            )
        )

    assert result.access_token == "access-token"
    assert result.refresh_token == "refresh-token"
    assert result.token_type == "bearer"

    getattr(user_repository, lookup_method).assert_awaited_once_with(
        identifier
    )

    token_repository.save_refresh_token.assert_awaited_once_with(
        jti="test-jti",
        user_id=user.id,
        expires_at=token_repository.save_refresh_token.call_args.kwargs[
            "expires_at"
        ],
    )


@pytest.mark.asyncio
async def test_login_user_not_found(service, user_repository):
    user_repository.get_by_email.return_value = None

    with pytest.raises(InvalidCredentialsError):
        await service.login(
            UserLogin(
                identifier="test@example.com",
                password="password123",
            )
        )

    user_repository.get_by_email.assert_awaited_once()
    user_repository.get_by_username.assert_not_awaited()


@pytest.mark.asyncio
async def test_login_invalid_password(
    service,
    user_repository,
    user,
    token_repository,
):
    user_repository.get_by_email.return_value = user

    with patch.object(PasswordHasher, "verify", side_effect=VerifyMismatchError):
        with pytest.raises(InvalidCredentialsError):
            await service.login(
                UserLogin(
                    identifier="test@example.com",
                    password="wrong-password",
                )
            )

    token_repository.save_refresh_token.assert_not_awaited()


# =========================
# DELETE
# =========================

@pytest.mark.asyncio
async def test_delete_user(service, user_repository, user):
    user_repository.get_by_user_id.return_value = user

    await service.delete(user_id=user.id)

    assert user.is_active is False

    user_repository.get_by_user_id.assert_awaited_once_with(
        id=user.id
    )


@pytest.mark.asyncio
async def test_delete_user_not_found(service, user_repository):
    user_repository.get_by_user_id.return_value = None

    with pytest.raises(UserNotFoundError):
        await service.delete(user_id=999)

    user_repository.get_by_user_id.assert_awaited_once_with(
        id=999
    )


@pytest.mark.asyncio
async def test_delete_already_deleted_user(
    service,
    user_repository,
    user,
):
    user.is_active = False
    user_repository.get_by_user_id.return_value = user

    with pytest.raises(UserAlreadyDeletedError):
        await service.delete(user_id=user.id)

    assert user.is_active is False


# =========================
# LOGOUT
# =========================

@pytest.mark.asyncio
async def test_logout(
    service,
    token_repository,
):
    refresh_token = "valid-refresh-token"

    with patch(
        "auth.services.verify_token",
        return_value={"jti": "test-jti"},
    ) as verify_mock:

        await service.logout(
            RefreshTokenRequest(refresh_token=refresh_token)
        )

    verify_mock.assert_called_once_with(
        refresh_token,
        expected_type="refresh",
    )

    token_repository.revoke_token_by_jti.assert_awaited_once_with(
        jti="test-jti"
    )


@pytest.mark.asyncio
async def test_logout_invalid_token(
    service,
    token_repository,
):
    with patch(
        "auth.services.verify_token",
        return_value=None,
    ):
        with pytest.raises(InvalidTokenError):
            await service.logout(
                RefreshTokenRequest(
                    refresh_token="invalid-token"
                )
            )

    token_repository.revoke_token_by_jti.assert_not_awaited()