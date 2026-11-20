"""
API-интеграционные тесты домена teams (TestClient + реальная БД).

Сценарии:
- happy path: create_team -> join by invite code -> get members
- 404: несуществующая команда
- 403: участник, не являющийся менеджером, пытается изменить команду
- 401: анонимный доступ без токена
"""

import uuid

from fastapi.testclient import TestClient

TEAMS_BASE = "/api/v1/team"


def _payload(suffix: str) -> dict:
    return {
        "username": f"teamuser_{suffix}",
        "email": f"teamuser_{suffix}@example.com",
        "password": "password123",
        "first_name": "Team",
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
        f"{TEAMS_BASE}/",
        json={"name": name},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


# --- happy path: create team -> join by invite code -> read members -----------


def test_teams_happy_path_create_join_and_read_members(client: TestClient):
    manager = _register_and_login(client, uuid.uuid4().hex[:8])
    team = _create_team(client, manager["token"], "Happy Team")

    assert team["id"] is not None
    assert team["invite_code"]

    joiner = _register_and_login(client, uuid.uuid4().hex[:8])
    join_resp = client.get(
        f"{TEAMS_BASE}/{team['id']}/join/{team['invite_code']}",
        headers=_auth_headers(joiner["token"]),
    )
    assert join_resp.status_code == 200, join_resp.text

    members_resp = client.get(
        f"{TEAMS_BASE}/{team['id']}/members",
        headers=_auth_headers(manager["token"]),
    )
    assert members_resp.status_code == 200, members_resp.text

    members = members_resp.json()
    assert len(members) == 2
    roles = {member["role"] for member in members}
    assert "manager" in roles
    assert "member" in roles


# --- 404: team not found ---------------------------------------------------------


def test_teams_get_team_not_found_returns_404(client: TestClient):
    user = _register_and_login(client, uuid.uuid4().hex[:8])

    resp = client.get(
        f"{TEAMS_BASE}/999999",
        headers=_auth_headers(user["token"]),
    )

    assert resp.status_code == 404
    assert resp.json()["error"] == "not_found"


def test_teams_members_not_found_returns_404(client: TestClient):
    user = _register_and_login(client, uuid.uuid4().hex[:8])

    resp = client.get(
        f"{TEAMS_BASE}/999999/members",
        headers=_auth_headers(user["token"]),
    )

    assert resp.status_code == 404
    assert resp.json()["error"] == "not_found"


# --- 403: only manager can update team ------------------------------------------


def test_teams_update_by_member_returns_403(client: TestClient):
    manager = _register_and_login(client, uuid.uuid4().hex[:8])
    team = _create_team(client, manager["token"], "Forbidden Team")

    joiner = _register_and_login(client, uuid.uuid4().hex[:8])
    join_resp = client.get(
        f"{TEAMS_BASE}/{team['id']}/join/{team['invite_code']}",
        headers=_auth_headers(joiner["token"]),
    )
    assert join_resp.status_code == 200

    resp = client.put(
        f"{TEAMS_BASE}/{team['id']}",
        json={"id": team["id"], "name": "Hacked Team"},
        headers=_auth_headers(joiner["token"]),
    )

    assert resp.status_code == 403
    assert resp.json()["error"] == "permission_denied"


# --- 401: anonymous access --------------------------------------------------------


def test_teams_get_team_without_token_returns_401(client: TestClient):
    resp = client.get(f"{TEAMS_BASE}/1")

    assert resp.status_code == 401
