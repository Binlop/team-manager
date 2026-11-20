"""
API-интеграционные тесты домена auth (TestClient + реальная БД).

Сценарий happy path: register -> login -> /me -> refresh_token -> logout.
"""

import uuid

from fastapi.testclient import TestClient
from core.security import verify_token

AUTH_BASE = "/api/v1/auth"


def _credentials(suffix: str) -> dict:
    return {
        "username": f"authuser_{suffix}",
        "email": f"authuser_{suffix}@example.com",
        "password": "password123",
        "first_name": "Auth",
        "last_name": "User",
    }


def _register(client: TestClient, suffix: str) -> tuple[str, dict]:
    credentials = _credentials(suffix)
    resp = client.post(f"{AUTH_BASE}/register", json=credentials)
    assert resp.status_code == 201, resp.text
    return credentials["username"], resp.json()


def _login(client: TestClient, identifier: str, password: str = "password123") -> dict:
    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"identifier": identifier, "password": password},
    )
    return resp.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- happy path: register -> login -> me -> refresh -> logout -----------------


def test_auth_happy_path_register_and_login(client: TestClient):
    username, _body = _register(client, uuid.uuid4().hex[:8])
    tokens = _login(client, username)

    access_payload = verify_token(tokens["access_token"], expected_type="access")
    refresh_payload = verify_token(tokens["refresh_token"], expected_type="refresh")

    assert access_payload["sub"].isdigit()
    assert refresh_payload["jti"]


def test_auth_happy_path_me_returns_username(client: TestClient):
    username, _body = _register(client, uuid.uuid4().hex[:8])
    tokens = _login(client, username)

    resp = client.get(f"{AUTH_BASE}/me", headers=_auth_headers(tokens["access_token"]))

    assert resp.status_code == 200
    assert resp.json() == username


def test_auth_happy_path_refresh_token_rotates(client: TestClient):
    username, _body = _register(client, uuid.uuid4().hex[:8])
    tokens = _login(client, username)
    old_refresh_payload = verify_token(tokens["refresh_token"], expected_type="refresh")

    resp = client.post(
        f"{AUTH_BASE}/refresh_token",
        params={"refresh_token": tokens["refresh_token"]},
    )

    assert resp.status_code == 200, resp.text
    new_tokens = resp.json()
    new_refresh_payload = verify_token(new_tokens["refresh_token"], expected_type="refresh")
    assert new_refresh_payload["jti"] != old_refresh_payload["jti"]


def test_auth_happy_path_logout_revokes_refresh_token(client: TestClient):
    username, _body = _register(client, uuid.uuid4().hex[:8])
    tokens = _login(client, username)

    resp = client.post(f"{AUTH_BASE}/logout", params={"refresh_token": tokens["refresh_token"]})

    assert resp.status_code == 204

    resp = client.post(
        f"{AUTH_BASE}/refresh_token",
        params={"refresh_token": tokens["refresh_token"]},
    )

    assert resp.status_code == 401


# --- error paths -------------------------------------------------------------


def test_auth_me_with_invalid_token_returns_401(client: TestClient):
    resp = client.get(f"{AUTH_BASE}/me", headers={"Authorization": "Bearer invalid.token.here"})

    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_token"


def test_auth_me_without_token_returns_401(client: TestClient):
    resp = client.get(f"{AUTH_BASE}/me")

    assert resp.status_code == 401


def test_auth_register_duplicate_email_returns_409(client: TestClient):
    suffix = uuid.uuid4().hex[:8]
    username, _body = _register(client, suffix)
    credentials = _credentials(uuid.uuid4().hex[:8])
    credentials["email"] = f"authuser_{suffix}@example.com"  # email уже занят -> конфликт

    resp = client.post(f"{AUTH_BASE}/register", json=credentials)

    assert resp.status_code == 409
    assert resp.json()["error"] == "email_already_exists"


def test_auth_login_wrong_password_returns_401(client: TestClient):
    username, _body = _register(client, uuid.uuid4().hex[:8])

    resp = client.post(
        f"{AUTH_BASE}/login",
        json={"identifier": username, "password": "wrong-password"},
    )

    assert resp.status_code == 401
    assert resp.json()["error"] == "invalid_credentials"


def test_auth_register_with_short_password_returns_422(client: TestClient):
    resp = client.post(
        f"{AUTH_BASE}/register",
        json={
            "username": f"authuser_{uuid.uuid4().hex[:8]}",
            "email": f"authuser_{uuid.uuid4().hex[:8]}@example.com",
            "password": "short",
            "first_name": "Auth",
            "last_name": "User",
        },
    )

    assert resp.status_code == 422
