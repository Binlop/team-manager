import pytest

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from auth.services import TokenService
from auth.schemas import RefreshTokenRequest
from auth.exceptions import InvalidTokenError


@pytest.fixture
def uow():
    return MagicMock()


@pytest.fixture
def service(uow):
    service = TokenService(uow)
    service.token_repository = AsyncMock()
    return service


@pytest.fixture
def refresh_request():
    return RefreshTokenRequest(
        refresh_token="valid-refresh-token"
    )


@pytest.fixture
def token():
    return MagicMock(
        id=1,
        jti="test-jti",
        user_id=10,
        revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    )


# =========================
# UPDATE REFRESH TOKEN
# =========================

@pytest.mark.asyncio
async def test_update_refresh_token(
    service,
    refresh_request,
    token,
):
    service.token_repository.get_token_by_jti.return_value = token

    expires_at = datetime.now(timezone.utc) + timedelta(days=30)

    with (
        patch(
            "auth.services.verify_token",
            return_value={
                "jti": "test-jti",
                "sub": "10",
            },
        ),
        patch(
            "auth.services.create_access_token",
            return_value="new-access-token",
        ),
        patch(
            "auth.services.create_refresh_token",
            return_value=(
                "new-refresh-token",
                "new-jti",
                expires_at,
            ),
        ),
    ):
        result = await service.update_refresh_token(
            refresh_request
        )

    assert result.access_token == "new-access-token"
    assert result.refresh_token == "new-refresh-token"
    assert result.token_type == "bearer"

    service.token_repository.get_token_by_jti.assert_awaited_once_with(
        jti="test-jti"
    )

    service.token_repository.revoke_token_by_jti.assert_awaited_once_with(
        jti="test-jti"
    )

    service.token_repository.save_refresh_token.assert_awaited_once_with(
        jti="new-jti",
        user_id=10,
        expires_at=expires_at,
    )


@pytest.mark.asyncio
async def test_update_refresh_token_invalid_jwt(
    service,
    refresh_request,
):
    with patch(
        "auth.services.verify_token",
        return_value=None,
    ):
        with pytest.raises(InvalidTokenError):
            await service.update_refresh_token(refresh_request)

    service.token_repository.get_token_by_jti.assert_not_awaited()
    service.token_repository.revoke_token_by_jti.assert_not_awaited()
    service.token_repository.save_refresh_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_refresh_token_not_found(
    service,
    refresh_request,
):
    service.token_repository.get_token_by_jti.return_value = None

    with patch(
        "auth.services.verify_token",
        return_value={
            "jti": "unknown-jti",
            "sub": "10",
        },
    ):
        with pytest.raises(InvalidTokenError):
            await service.update_refresh_token(refresh_request)

    service.token_repository.revoke_token_by_jti.assert_not_awaited()
    service.token_repository.revoke_all_for_user.assert_not_awaited()
    service.token_repository.save_refresh_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_revoked_token(
    service,
    refresh_request,
    token,
):
    token.revoked = True

    service.token_repository.get_token_by_jti.return_value = token

    with patch(
        "auth.services.verify_token",
        return_value={
            "jti": "test-jti",
            "sub": "10",
        },
    ):
        with pytest.raises(InvalidTokenError):
            await service.update_refresh_token(refresh_request)

    service.token_repository.revoke_all_for_user.assert_awaited_once_with(
        user_id=10
    )

    service.token_repository.revoke_token_by_jti.assert_not_awaited()
    service.token_repository.save_refresh_token.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_expired_token(
    service,
    refresh_request,
    token,
):
    token.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

    service.token_repository.get_token_by_jti.return_value = token

    with patch(
        "auth.services.verify_token",
        return_value={
            "jti": "test-jti",
            "sub": "10",
        },
    ):
        with pytest.raises(InvalidTokenError):
            await service.update_refresh_token(refresh_request)

    service.token_repository.revoke_token_by_jti.assert_not_awaited()
    service.token_repository.revoke_all_for_user.assert_not_awaited()
    service.token_repository.save_refresh_token.assert_not_awaited()