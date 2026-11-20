"""
API-интеграционные тесты домена meetings (TestClient + реальная БД).

Сценарии:
- POST /api/v1/meeting/ с ends_at == starts_at -> 422 (валидация интервала)
"""

import uuid

from fastapi.testclient import TestClient

MEETINGS_BASE = "/api/v1/meeting"


def _payload(suffix: str) -> dict:
    return {
        "username": f"meetinguser_{suffix}",
        "email": f"meetinguser_{suffix}@example.com",
        "password": "password123",
        "first_name": "Meeting",
        "last_name": "User",
    }


def _register_and_login(client: TestClient, suffix: str) -> dict:
    payload = _payload(suffix)
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text

    tokens = _login(client, payload["username"])
    return {
        "username": payload["username"],
        "token": tokens["access_token"],
    }


def _login(client: TestClient, identifier: str, password: str = "password123") -> dict:
    resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# --- 422: интервал встречи должен быть непустым (ends_at > starts_at) ---------


def test_meeting_create_with_equal_start_and_end_returns_422(client: TestClient):
    user = _register_and_login(client, uuid.uuid4().hex[:8])

    resp = client.post(
        f"{MEETINGS_BASE}/",
        json={
            "name": "Zero-length meeting",
            "starts_at": "2030-01-01T10:00:00Z",
            "ends_at": "2030-01-01T10:00:00Z",
            "status": "scheduled",
        },
        headers=_auth_headers(user["token"]),
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "validation_error"
