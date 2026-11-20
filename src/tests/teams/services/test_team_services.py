from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.exceptions import PermissionDeniedError
from teams.exceptions import TeamNotFoundError
from teams.schemas import TeamBase, TeamUpdate
from teams.services import TeamService, hash_invite_code

pytestmark = pytest.mark.asyncio

INVITE_CODE = "RawInvite01"


@pytest.fixture
def service(team_repo, user_repo):
    return TeamService(team_repo=team_repo, user_repo=user_repo)


@pytest.fixture
def data():
    return TeamBase(name="Alpha")


@pytest.fixture
def update_data(team):
    return TeamUpdate(id=team.id, name="Alpha 2")


# --- get_team_or_404 --------------------------------------------------------


async def test_get_team_or_404(service, team_repo, manager, team):
    team_repo.get_team_for_user.return_value = team

    result = await service.get_team_or_404(team.id, manager)

    assert result.id == team.id
    assert result.name == team.name
    team_repo.get_team_for_user.assert_awaited_once_with(team.id, manager.id)


async def test_get_team_or_404_not_found(service, team_repo, manager):
    team_repo.get_team_for_user.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.get_team_or_404(10, manager)


# --- get_team_members -------------------------------------------------------


async def test_get_team_members(service, team_repo, manager, team):
    members = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    team_repo.get_team_for_user.return_value = team
    team_repo.get_team_members.return_value = members

    result = await service.get_team_members(team.id, manager)

    assert result == members
    team_repo.get_team_for_user.assert_awaited_once_with(team.id, manager.id)
    team_repo.get_team_members.assert_awaited_once_with(
        team_id=team.id, user_id=manager.id
    )


async def test_get_team_members_team_not_found(service, team_repo, manager):
    team_repo.get_team_for_user.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.get_team_members(10, manager)

    team_repo.get_team_members.assert_not_awaited()


# --- create_team ------------------------------------------------------------


async def test_create_team(service, team_repo, data, manager):
    created = SimpleNamespace(
        id=11,
        name=data.name,
        manager_id=manager.id,
        manager=SimpleNamespace(id=manager.id, first_name="Man", last_name="Ager"),
    )
    team = SimpleNamespace(
        id=created.id,
        name=data.name,
        manager_id=manager.id,
        manager=created.manager,
    )
    team_repo.create_team.return_value = created
    team_repo.get_team_for_user.return_value = team

    with patch.object(
        TeamService, "generate_invite_code", return_value=INVITE_CODE
    ) as generate:
        result = await service.create_team(data, manager)

    assert result.invite_code == INVITE_CODE
    assert result.name == data.name
    generate.assert_called_once_with()
    team_repo.create_team.assert_awaited_once_with(
        data, manager.id, hash_invite_code(INVITE_CODE)
    )
    team_repo.get_team_for_user.assert_awaited_once_with(created.id, manager.id)


async def test_create_team_not_found_after_creation(service, team_repo, data, manager):
    created = SimpleNamespace(id=11)
    team_repo.create_team.return_value = created
    team_repo.get_team_for_user.return_value = None

    with patch.object(TeamService, "generate_invite_code", return_value=INVITE_CODE):
        with pytest.raises(TeamNotFoundError):
            await service.create_team(data, manager)


async def test_create_team_stores_only_hashed_invite_code(
    service, team_repo, data, manager
):
    created = SimpleNamespace(id=11, name=data.name)
    team_repo.create_team.return_value = created
    team_repo.get_team_for_user.return_value = SimpleNamespace(
        id=created.id,
        name=data.name,
        manager=SimpleNamespace(id=manager.id, first_name="Man", last_name="Ager"),
    )

    with patch.object(TeamService, "generate_invite_code", return_value=INVITE_CODE):
        await service.create_team(data, manager)

    passed_code = team_repo.create_team.await_args.args[2]
    assert passed_code != INVITE_CODE
    assert passed_code == hash_invite_code(INVITE_CODE)


# --- update_team ------------------------------------------------------------


async def test_update_team(service, team_repo, update_data, manager, team):
    updated = SimpleNamespace(id=team.id, name=update_data.name)
    refreshed = SimpleNamespace(id=team.id, name=update_data.name)
    team_repo.get_team_for_user.side_effect = [team, refreshed]
    team_repo.update_team.return_value = updated

    result = await service.update_team(team.id, update_data, manager)

    assert result is refreshed
    team_repo.get_team_for_user.assert_any_await(team.id, manager.id)
    team_repo.update_team.assert_awaited_once_with(
        team.id, update_data, manager.id
    )
    assert team_repo.get_team_for_user.await_count == 2


async def test_update_team_not_found(service, team_repo, update_data, manager):
    team_repo.get_team_for_user.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.update_team(10, update_data, manager)

    team_repo.update_team.assert_not_awaited()


async def test_update_team_by_non_manager(
    service, team_repo, update_data, stranger, team
):
    team_repo.get_team_for_user.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.update_team(team.id, update_data, stranger)

    team_repo.update_team.assert_not_awaited()


async def test_update_team_returns_not_found_if_repository_did_not_update(
    service, team_repo, update_data, manager, team
):
    team_repo.get_team_for_user.return_value = team
    team_repo.update_team.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.update_team(team.id, update_data, manager)


# --- refresh_invite_code ----------------------------------------------------


async def test_refresh_invite_code(service, team_repo, manager, team):
    team_repo.get_team_for_user.return_value = team
    team_repo.update_invite_code_team.return_value = team

    with patch.object(
        TeamService, "generate_invite_code", return_value=INVITE_CODE
    ) as generate:
        result = await service.refresh_invite_code(team.id, manager)

    assert result.invite_code == INVITE_CODE
    generate.assert_called_once_with()
    team_repo.update_invite_code_team.assert_awaited_once_with(
        team.id, hash_invite_code(INVITE_CODE), manager.id
    )


async def test_refresh_invite_code_team_not_found(service, team_repo, manager):
    team_repo.get_team_for_user.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.refresh_invite_code(10, manager)

    team_repo.update_invite_code_team.assert_not_awaited()


async def test_refresh_invite_code_by_non_manager(
    service, team_repo, stranger, team
):
    team_repo.get_team_for_user.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.refresh_invite_code(team.id, stranger)

    team_repo.update_invite_code_team.assert_not_awaited()


async def test_refresh_invite_code_repository_did_not_update(
    service, team_repo, manager, team
):
    team_repo.get_team_for_user.return_value = team
    team_repo.update_invite_code_team.return_value = None

    with patch.object(TeamService, "generate_invite_code", return_value=INVITE_CODE):
        with pytest.raises(TeamNotFoundError):
            await service.refresh_invite_code(team.id, manager)
