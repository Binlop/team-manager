from types import SimpleNamespace

import pytest

from core.exceptions import PermissionDeniedError
from teams.exceptions import (
    CannotRemoveManagerError,
    TeamMemberAlreadyExistsError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
)
from teams.models import TeamRole
from teams.schemas import TeamMemberCreate, TeamMemberUpdate
from teams.services import TeamMemberService

pytestmark = pytest.mark.asyncio

USER_ID = 5
MEMBER_ID = 100


@pytest.fixture
def service(team_repo, team_member_repo):
    return TeamMemberService(team_repo=team_repo, team_member_repo=team_member_repo)


@pytest.fixture
def member(team):
    return SimpleNamespace(
        id=MEMBER_ID, user_id=USER_ID, team_id=team.id, role=TeamRole.MEMBER
    )


# --- add_member -------------------------------------------------------------

@pytest.fixture
def add_data(team):
    return TeamMemberCreate(user_id=USER_ID, team_id=team.id, role=TeamRole.MEMBER)


async def test_add_member(service, team_repo, team_member_repo, add_data, manager, team, member):
    team_repo.get_team_by_id.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False
    team_member_repo.add_team_member.return_value = member
    team_member_repo.get_member_by_id.return_value = member

    result = await service.add_member(add_data, manager)

    assert result is member
    team_member_repo.check_member_exists_with_user_id_and_team_id.assert_awaited_once_with(
        USER_ID, team.id
    )
    team_member_repo.add_team_member.assert_awaited_once_with(add_data)
    team_member_repo.get_member_by_id.assert_awaited_once_with(member_id=member.id)


async def test_add_member_team_not_found(service, team_repo, team_member_repo, add_data, manager):
    team_repo.get_team_by_id.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.add_member(add_data, manager)

    team_member_repo.add_team_member.assert_not_awaited()


async def test_add_member_by_non_manager(
    service, team_repo, team_member_repo, add_data, stranger, team
):
    team_repo.get_team_by_id.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.add_member(add_data, stranger)

    team_member_repo.add_team_member.assert_not_awaited()


async def test_add_member_already_exists(
    service, team_repo, team_member_repo, add_data, manager, team
):
    team_repo.get_team_by_id.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = True

    with pytest.raises(TeamMemberAlreadyExistsError):
        await service.add_member(add_data, manager)

    team_member_repo.add_team_member.assert_not_awaited()


async def test_add_member_not_found_after_creation(
    service, team_repo, team_member_repo, add_data, manager, team, member
):
    team_repo.get_team_by_id.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False
    team_member_repo.add_team_member.return_value = member
    team_member_repo.get_member_by_id.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.add_member(add_data, manager)


# --- update_member_role -----------------------------------------------------

@pytest.fixture
def update_data(team):
    return TeamMemberUpdate(id=MEMBER_ID, team_id=team.id, role=TeamRole.MEMBER)


async def test_update_member_role_team_not_found(
    service, team_repo, team_member_repo, update_data, manager
):
    team_repo.get_team_by_id.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.update_member_role(update_data, manager)

    team_member_repo.update_member_role.assert_not_awaited()


async def test_update_member_role_by_non_manager(
    service, team_repo, team_member_repo, update_data, stranger, team
):
    team_repo.get_team_by_id.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.update_member_role(update_data, stranger)

    team_member_repo.update_member_role.assert_not_awaited()


async def test_update_member_role_member_not_found(
    service, team_repo, team_member_repo, update_data, manager, team
):
    team_repo.get_team_by_id.return_value = team
    team_member_repo.update_member_role.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.update_member_role(update_data, manager)


async def test_update_member_role_to_non_manager_role(
    service, team_repo, team_member_repo, update_data, manager, team, member
):
    fresh = SimpleNamespace(id=member.id, role=TeamRole.MEMBER)
    team_repo.get_team_by_id.return_value = team
    team_member_repo.update_member_role.return_value = member  # role = MEMBER
    team_member_repo.get_member_by_id.return_value = fresh

    result = await service.update_member_role(update_data, manager)

    assert result is fresh
    team_member_repo.update_member_role.assert_awaited_once_with(member=update_data)
    # прежнего менеджера не трогаем
    team_member_repo.get_member_by_team_and_user_id.assert_not_awaited()
    team_member_repo.get_member_by_id.assert_awaited_once_with(member.id)


async def test_update_member_role_to_manager_demotes_previous_manager(
    service, team_repo, team_member_repo, manager, team
):
    data = TeamMemberUpdate(id=MEMBER_ID, team_id=team.id, role=TeamRole.MANAGER)
    promoted = SimpleNamespace(
        id=MEMBER_ID, user_id=USER_ID, team_id=team.id, role=TeamRole.MANAGER
    )
    previous_manager = SimpleNamespace(id=200)
    fresh = SimpleNamespace(id=MEMBER_ID, role=TeamRole.MANAGER)
    team_repo.get_team_by_id.return_value = team
    team_member_repo.update_member_role.return_value = promoted
    team_member_repo.get_member_by_team_and_user_id.return_value = previous_manager
    team_member_repo.get_member_by_id.return_value = fresh

    result = await service.update_member_role(data, manager)

    assert result is fresh
    team_member_repo.get_member_by_team_and_user_id.assert_awaited_once_with(
        team_id=team.id, user_id=manager.id
    )
    assert team_member_repo.update_member_role.await_count == 2
    team_member_repo.update_member_role.assert_any_await(member=data)
    team_member_repo.update_member_role.assert_any_await(
        member=TeamMemberUpdate(id=200, team_id=team.id, role=TeamRole.MEMBER)
    )


async def test_update_member_role_to_manager_previous_manager_not_found(
    service, team_repo, team_member_repo, manager, team
):
    data = TeamMemberUpdate(id=MEMBER_ID, team_id=team.id, role=TeamRole.MANAGER)
    promoted = SimpleNamespace(
        id=MEMBER_ID, user_id=USER_ID, team_id=team.id, role=TeamRole.MANAGER
    )
    team_repo.get_team_by_id.return_value = team
    team_member_repo.update_member_role.return_value = promoted
    team_member_repo.get_member_by_team_and_user_id.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.update_member_role(data, manager)


# @pytest.mark.xfail(
#     reason="Баг: если менеджер назначает менеджером самого себя, сервис "
#     "тут же понижает его до MEMBER (обновляет ту же запись второй раз).",
# )
async def test_update_member_role_manager_assigning_self_is_not_demoted(
    service, team_repo, team_member_repo, manager, team
):
    manager_member = SimpleNamespace(
        id=200, user_id=manager.id, team_id=team.id, role=TeamRole.MANAGER
    )
    data = TeamMemberUpdate(id=200, team_id=team.id, role=TeamRole.MANAGER)
    team_repo.get_team_by_id.return_value = team
    team_member_repo.update_member_role.return_value = manager_member
    team_member_repo.get_member_by_team_and_user_id.return_value = manager_member
    team_member_repo.get_member_by_id.return_value = manager_member

    await service.update_member_role(data, manager)

    assert team_member_repo.update_member_role.await_count == 1


# --- remove_member ----------------------------------------------------------

async def test_remove_member(service, team_repo, team_member_repo, manager, team, member):
    team_repo.get_team_by_id.return_value = team
    team_member_repo.get_member_by_team_and_user_id.return_value = member
    team_member_repo.remove_member.return_value = True

    result = await service.remove_member(team.id, USER_ID, manager)

    assert result is None
    team_member_repo.get_member_by_team_and_user_id.assert_awaited_once_with(team.id, USER_ID)
    team_member_repo.remove_member.assert_awaited_once_with(user_id=USER_ID, team_id=team.id)


async def test_remove_member_team_not_found(service, team_repo, team_member_repo, manager):
    team_repo.get_team_by_id.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.remove_member(10, USER_ID, manager)

    team_member_repo.remove_member.assert_not_awaited()


async def test_remove_member_by_non_manager(
    service, team_repo, team_member_repo, stranger, team
):
    team_repo.get_team_by_id.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.remove_member(team.id, USER_ID, stranger)

    team_member_repo.remove_member.assert_not_awaited()


async def test_remove_member_not_found(service, team_repo, team_member_repo, manager, team):
    team_repo.get_team_by_id.return_value = team
    team_member_repo.get_member_by_team_and_user_id.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.remove_member(team.id, USER_ID, manager)

    team_member_repo.remove_member.assert_not_awaited()


# Сервис сравнивает роль со строками 'manager' и 'admin'.
@pytest.mark.parametrize("role", ["manager", "admin"])
async def test_remove_member_cannot_remove_manager_or_admin(
    service, team_repo, team_member_repo, manager, team, role
):
    privileged = SimpleNamespace(id=MEMBER_ID, user_id=USER_ID, team_id=team.id, role=role)
    team_repo.get_team_by_id.return_value = team
    team_member_repo.get_member_by_team_and_user_id.return_value = privileged

    with pytest.raises(CannotRemoveManagerError):
        await service.remove_member(team.id, USER_ID, manager)

    team_member_repo.remove_member.assert_not_awaited()


async def test_remove_member_repository_removed_nothing(
    service, team_repo, team_member_repo, manager, team, member
):
    team_repo.get_team_by_id.return_value = team
    team_member_repo.get_member_by_team_and_user_id.return_value = member
    team_member_repo.remove_member.return_value = False

    with pytest.raises(TeamMemberNotFoundError):
        await service.remove_member(team.id, USER_ID, manager)