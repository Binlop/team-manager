from types import SimpleNamespace

import pytest

from auth.exceptions import UserNotFoundError
from core.exceptions import PermissionDeniedError
from teams.exceptions import InviteCodeAlreadyExistsError, TeamNotFoundError
from teams.schemas import TeamCreate, TeamUpdate
from teams.services import TeamService

pytestmark = pytest.mark.asyncio



@pytest.fixture
def service(team_repo, user_repo):
    return TeamService(team_repo=team_repo, user_repo=user_repo,)


@pytest.fixture
def data(manager):
    return TeamCreate(name="Alpha", invite_code="ALPHA1", manager_id=manager.id)

@pytest.fixture
def update_data():
    return TeamUpdate(name="Alpha2", invite_code="NECODE")

# --- get_team_members -------------------------------------------------------

async def test_get_team_members(service, team_repo):
    members = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    team_repo.get_team_members.return_value = members

    result = await service.get_team_members(10)

    assert result == members
    team_repo.get_team_members.assert_awaited_once_with(team_id=10)


# --- create_team ------------------------------------------------------------

async def test_create_team(service, team_repo, user_repo, data, manager, team):
    team_repo.get_team_by_invite_code.return_value = None
    user_repo.get_by_user_id.return_value = manager
    team_repo.create_team.return_value = team

    result = await service.create_team(data)

    assert result is team
    team_repo.get_team_by_invite_code.assert_awaited_once_with(data.invite_code)
    user_repo.get_by_user_id.assert_awaited_once_with(data.manager_id)
    team_repo.create_team.assert_awaited_once_with(data)


async def test_create_team_invite_code_already_exists(service, team_repo, user_repo, data, team):
    team_repo.get_team_by_invite_code.return_value = team

    with pytest.raises(InviteCodeAlreadyExistsError):
        await service.create_team(data)

    user_repo.get_by_user_id.assert_not_awaited()
    team_repo.create_team.assert_not_awaited()


async def test_create_team_manager_not_found(service, team_repo, user_repo, data):
    team_repo.get_team_by_invite_code.return_value = None
    user_repo.get_by_user_id.return_value = None

    with pytest.raises(UserNotFoundError):
        await service.create_team(data)

    team_repo.create_team.assert_not_awaited()


# --- update_team ------------------------------------------------------------

async def test_update_team(service, team_repo, update_data, manager, team):
    updated = SimpleNamespace(id=team.id, name="Alpha2")
    team_repo.get_team_by_id.return_value = team
    team_repo.get_team_by_invite_code.return_value = None   
    team_repo.update_team.return_value = updated

    result = await service.update_team(team.id, update_data, manager)

    assert result is updated
    team_repo.get_team_by_invite_code.assert_awaited_once_with("NECODE")
    team_repo.update_team.assert_awaited_once_with(team_id=team.id, team=update_data)


async def test_update_team_same_invite_code_skips_uniqueness_check(
    service, team_repo, manager, team
):
    data = TeamUpdate(name="Alpha2", invite_code=team.invite_code)
    team_repo.get_team_by_id.return_value = team

    await service.update_team(team.id, data, manager)

    team_repo.get_team_by_invite_code.assert_not_awaited()
    team_repo.update_team.assert_awaited_once_with(team_id=team.id, team=data)


async def test_update_team_invite_code_already_taken(
    service, team_repo, update_data, manager, team
):
    team_repo.get_team_by_id.return_value = team
    team_repo.get_team_by_invite_code.return_value = SimpleNamespace(id=99)

    with pytest.raises(InviteCodeAlreadyExistsError):
        await service.update_team(team.id, update_data, manager)

    team_repo.update_team.assert_not_awaited()


async def test_update_team_not_found(service, team_repo, update_data, manager):
    team_repo.get_team_by_id.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.update_team(10, update_data, manager)

    team_repo.update_team.assert_not_awaited()


async def test_update_team_by_non_manager(
    service, team_repo, update_data, stranger, team
):
    team_repo.get_team_by_id.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.update_team(team.id, update_data, stranger)

    team_repo.update_team.assert_not_awaited()