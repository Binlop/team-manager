# NEW: Интеграционные happy-path тесты домена teams.
# Реальные репозитории + сервисы + БД (PostgreSQL через testcontainers, src/tests/conftest.py).
# Сценарий: create_team -> join_by_invite_code -> get_team_members.

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from auth.repositories import UserRepository
from teams.repositories import TeamMemberRepository, TeamRepository
from teams.schemas import TeamBase
from teams.services import TeamMemberService, TeamService


@pytest_asyncio.fixture
async def user_repo(uow):
    return UserRepository(uow)


@pytest_asyncio.fixture
async def team_repo(uow):
    return TeamRepository(uow)


@pytest_asyncio.fixture
async def team_member_repo(uow):
    return TeamMemberRepository(uow)


@pytest.fixture
def team_service(team_repo, user_repo):
    return TeamService(team_repo=team_repo, user_repo=user_repo)


@pytest.fixture
def member_service(team_repo, team_member_repo):
    return TeamMemberService(team_repo=team_repo, team_member_repo=team_member_repo)


# happy path — создание команды, join по invite-коду, чтение участников
@pytest.mark.asyncio
async def test_teams_happy_path_create_join_and_read_members(
    team_service, member_service, user, user_factory
):
    manager = user
    team = await team_service.create_team(TeamBase(name="Integration Team"), manager)
    assert team.id is not None
    assert team.name == "Integration Team"
    assert team.invite_code

    joiner = await user_factory(username="joiner", email="joiner@example.com")
    member = await member_service.add_member_by_invite_code(team.invite_code, joiner)
    assert member is not None

    members = await team_service.get_team_members(team.id, manager)

    assert len(members) == 2
    member_ids = {m.user_id for m in members}
    assert manager.id in member_ids
    assert joiner.id in member_ids
