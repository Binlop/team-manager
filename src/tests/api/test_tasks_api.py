"""
API-интеграционные тесты домена tasks (TestClient + реальная БД).

Сценарии:
- happy path: create_task -> update_task (score валидация)
- 422: score вне диапазона [1, 5] (защита на уровне схемы)
"""

import uuid

from fastapi.testclient import TestClient
from core.security import verify_token

TASKS_BASE = "/api/v1/tasks"


def _payload(suffix: str) -> dict:
    return {
        "username": f"taskuser_{suffix}",
        "email": f"taskuser_{suffix}@example.com",
        "password": "password123",
        "first_name": "Task",
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


def _create_team(client: TestClient, token: str, name: str) -> dict:
    resp = client.post(
        f"/api/v1/team/",
        json={"name": name},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _create_task(client: TestClient, token: str, team_id: int, user_id: int) -> int:
    resp = client.post(
        f"{TASKS_BASE}/",
        json={
            "title": "API task",
            "description": "Task created via API",
            "due_date": "2030-01-10",
            "status": "open",
            "score": None,
            "assignee_id": user_id,
            "team_id": team_id,
        },
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _update_task(client: TestClient, task_id: int, token: str, score: int) -> object:
    resp = client.put(
        f"{TASKS_BASE}/{task_id}",
        json={
            "id": task_id,
            "title": "Updated task",
            "description": "Updated description",
            "due_date": "2030-01-10",
            "status": "open",
            "score": score,
            "assignee_id": _current_user_id(token),
            "manager_comment": None,
        },
        headers=_auth_headers(token),
    )
    return resp


def _current_user_id(token: str) -> int:
    payload = verify_token(token, expected_type="access")
    assert payload is not None
    return int(payload["sub"])


# --- happy path: create task -> update task ---------------------------------


def test_tasks_happy_path_create_and_update_task(client: TestClient):
    manager = _register_and_login(client, uuid.uuid4().hex[:8])
    team = _create_team(client, manager["token"], "Task Happy Team")
    task_id = _create_task(client, manager["token"], team["id"], _current_user_id(manager["token"]))

    resp = client.put(
        f"{TASKS_BASE}/{task_id}",
        json={
            "id": task_id,
            "title": "Updated task",
            "description": "Updated description",
            "due_date": "2030-01-10",
            "status": "open",
            "score": None,
            "assignee_id": _current_user_id(manager["token"]),
            "manager_comment": None,
        },
        headers=_auth_headers(manager["token"]),
    )
    assert resp.status_code == 200, resp.text


# --- 422: score вне диапазона [1, 5] ----------------------------------------


def test_tasks_update_task_score_out_of_range_returns_422(client: TestClient):
    manager = _register_and_login(client, uuid.uuid4().hex[:8])
    team = _create_team(client, manager["token"], "Task Score Team")
    task_id = _create_task(client, manager["token"], team["id"], _current_user_id(manager["token"]))

    resp = _update_task(client, task_id, manager["token"], score=6)

    assert resp.status_code == 422
    body = resp.json()
    assert body["error"] == "validation_error"
