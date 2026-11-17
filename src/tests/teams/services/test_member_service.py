from types import SimpleNamespace

import pytest

from core.exceptions import PermissionDeniedError
from teams.exceptions import (
    CannotDemoteManagerError,
    CannotRemoveManagerError,
    InvalidInviteCodeError,
    TeamMemberAlreadyExistsError,
    TeamMemberNotFoundError,
    TeamNotFoundError,
)
from teams.models import TeamRole
from teams.schemas import TeamMemberCreate, TeamMemberUpdate
from teams.services import TeamMemberService, hash_invite_code

pytestmark = pytest.mark.asyncio

USER_ID = 5
MEMBER_ID = 100
MANAGER_MEMBER_ID = 200
INVITE_CODE = "RawInvite01"


@pytest.fixture
def service(team_repo, team_member_repo):
    return TeamMemberService(team_repo=team_repo, team_member_repo=team_member_repo)


@pytest.fixture
def user():
    """Пользователь, которого добавляют в команду/назначают участником."""
    return SimpleNamespace(id=USER_ID)


@pytest.fixture
def member(team):
    return SimpleNamespace(
        id=MEMBER_ID, user_id=USER_ID, team_id=team.id, role=TeamRole.MEMBER
    )


# --- add_member -------------------------------------------------------------


@pytest.fixture
def add_data(team):
    return TeamMemberCreate(user_id=USER_ID, team_id=team.id, role=TeamRole.MEMBER)


async def test_add_member(
    service, team_repo, team_member_repo, add_data, manager, team, member
):
    team_repo.get_team_for_user.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False
    team_member_repo.add_team_member.return_value = member
    team_member_repo.get_member_by_id.return_value = member

    result = await service.add_member(add_data, manager)

    assert result is member
    team_repo.get_team_for_user.assert_awaited_once_with(team.id, manager.id)
    team_member_repo.check_member_exists_with_user_id_and_team_id.assert_awaited_once_with(
        USER_ID, team.id
    )
    team_member_repo.add_team_member.assert_awaited_once_with(add_data)
    team_member_repo.get_member_by_id.assert_awaited_once_with(member_id=member.id)


async def test_add_member_team_not_found(
    service, team_repo, team_member_repo, add_data, manager
):
    team_repo.get_team_for_user.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.add_member(add_data, manager)

    team_member_repo.add_team_member.assert_not_awaited()


async def test_add_member_by_non_manager(
    service, team_repo, team_member_repo, add_data, stranger, team
):
    team_repo.get_team_for_user.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.add_member(add_data, stranger)

    team_member_repo.add_team_member.assert_not_awaited()


async def test_add_member_already_exists(
    service, team_repo, team_member_repo, add_data, manager, team
):
    team_repo.get_team_for_user.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = True

    with pytest.raises(TeamMemberAlreadyExistsError):
        await service.add_member(add_data, manager)

    team_member_repo.add_team_member.assert_not_awaited()


async def test_add_member_not_found_after_creation(
    service, team_repo, team_member_repo, add_data, manager, team, member
):
    team_repo.get_team_for_user.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False
    team_member_repo.add_team_member.return_value = member
    team_member_repo.get_member_by_id.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.add_member(add_data, manager)


# --- add_member_by_invite_code ----------------------------------------------


async def test_add_member_by_invite_code(
    service, team_repo, team_member_repo, user, team, member
):
    team_repo.get_team_by_invite_code.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False
    team_member_repo.add_team_member.return_value = member
    team_member_repo.get_member_by_id.return_value = member

    result = await service.add_member_by_invite_code(INVITE_CODE, user)

    assert result is member
    team_repo.get_team_by_invite_code.assert_awaited_once_with(
        hash_invite_code(INVITE_CODE)
    )
    team_member_repo.check_member_exists_with_user_id_and_team_id.assert_awaited_once_with(
        user.id, team.id
    )
    team_member_repo.add_team_member.assert_awaited_once_with(
        TeamMemberCreate(user_id=user.id, team_id=team.id)
    )
    team_member_repo.get_member_by_id.assert_awaited_once_with(member_id=member.id)


async def test_add_member_by_invalid_invite_code(
    service, team_repo, team_member_repo, user
):
    team_repo.get_team_by_invite_code.return_value = None

    with pytest.raises(InvalidInviteCodeError):
        await service.add_member_by_invite_code(INVITE_CODE, user)

    team_member_repo.add_team_member.assert_not_awaited()


async def test_add_member_by_invite_code_already_member(
    service, team_repo, team_member_repo, user, team
):
    team_repo.get_team_by_invite_code.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = True

    with pytest.raises(TeamMemberAlreadyExistsError):
        await service.add_member_by_invite_code(INVITE_CODE, user)

    team_member_repo.add_team_member.assert_not_awaited()


async def test_add_member_by_invite_code_not_found_after_creation(
    service, team_repo, team_member_repo, user, team, member
):
    team_repo.get_team_by_invite_code.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False
    team_member_repo.add_team_member.return_value = member
    team_member_repo.get_member_by_id.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.add_member_by_invite_code(INVITE_CODE, user)


# --- update_member_role -----------------------------------------------------


async def test_update_member_role_team_not_found(
    service, team_repo, team_member_repo, manager, team
):
    data = TeamMemberUpdate(id=MEMBER_ID, team_id=team.id, role=TeamRole.MEMBER)
    team_repo.get_team_for_user.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.update_member_role(data, manager)

    team_member_repo.update_member_role.assert_not_awaited()


async def test_update_member_role_by_non_manager(
    service, team_repo, team_member_repo, stranger, team
):
    data = TeamMemberUpdate(id=MEMBER_ID, team_id=team.id, role=TeamRole.MEMBER)
    team_repo.get_team_for_user.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.update_member_role(data, stranger)

    team_member_repo.update_member_role.assert_not_awaited()


async def test_update_member_role_member_not_found(
    service, team_repo, team_member_repo, manager, team
):
    data = TeamMemberUpdate(id=MEMBER_ID, team_id=team.id, role=TeamRole.MEMBER)
    team_repo.get_team_for_user.return_value = team
    team_member_repo.update_member_role.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.update_member_role(data, manager)


async def test_update_member_role_to_member(
    service, team_repo, team_member_repo, manager, team, member
):
    data = TeamMemberUpdate(id=member.id, team_id=team.id, role=TeamRole.MEMBER)
    team_repo.get_team_for_user.return_value = team
    team_member_repo.update_member_role.return_value = member
    team_member_repo.get_member_by_id.return_value = member

    result = await service.update_member_role(data, manager)

    assert result is member
    team_member_repo.update_member_role.assert_awaited_once_with(member=data)
    # Прежнего менеджера не трогаем.
    team_member_repo.get_member_by_team_and_user_id.assert_not_awaited()
    team_repo.update_team_manager.assert_not_awaited()
    team_member_repo.get_member_by_id.assert_awaited_once_with(member.id)


async def test_update_member_role_member_from_other_team(
    service, team_repo, team_member_repo, manager, team, member
):
    data = TeamMemberUpdate(id=member.id, team_id=team.id, role=TeamRole.MEMBER)
    other_team_member = SimpleNamespace(
        id=member.id, user_id=member.user_id, team_id=team.id + 1, role=TeamRole.MEMBER
    )
    team_repo.get_team_for_user.return_value = team
    team_member_repo.update_member_role.return_value = member
    team_member_repo.get_member_by_id.return_value = other_team_member

    with pytest.raises(TeamMemberNotFoundError):
        await service.update_member_role(data, manager)


async def test_update_member_role_cannot_demote_manager(
    service, team_repo, team_member_repo, manager, team
):
    data = TeamMemberUpdate(
        id=MANAGER_MEMBER_ID, team_id=team.id, role=TeamRole.MEMBER
    )
    demoted_self = SimpleNamespace(
        id=MANAGER_MEMBER_ID,
        user_id=manager.id,
        team_id=team.id,
        role=TeamRole.MEMBER,
    )
    team_repo.get_team_for_user.return_value = team
    team_member_repo.update_member_role.return_value = demoted_self

    with pytest.raises(CannotDemoteManagerError):
        await service.update_member_role(data, manager)

    team_member_repo.get_member_by_id.assert_not_awaited()


async def test_update_member_role_to_manager_demotes_previous_manager(
    service, team_repo, team_member_repo, manager, team, user
):
    data = TeamMemberUpdate(id=MEMBER_ID, team_id=team.id, role=TeamRole.MANAGER)
    promoted = SimpleNamespace(
        id=MEMBER_ID, user_id=user.id, team_id=team.id, role=TeamRole.MANAGER
    )
    previous_manager = SimpleNamespace(id=MANAGER_MEMBER_ID)
    fresh = SimpleNamespace(
        id=MEMBER_ID, user_id=user.id, team_id=team.id, role=TeamRole.MANAGER
    )
    team_repo.get_team_for_user.return_value = team
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
        member=TeamMemberUpdate(
            id=previous_manager.id, team_id=team.id, role=TeamRole.MEMBER
        )
    )
    team_repo.update_team_manager.assert_awaited_once_with(
        team_id=team.id, manager_id=user.id
    )


async def test_update_member_role_to_manager_previous_manager_not_found(
    service, team_repo, team_member_repo, manager, team, user
):
    data = TeamMemberUpdate(id=MEMBER_ID, team_id=team.id, role=TeamRole.MANAGER)
    promoted = SimpleNamespace(
        id=MEMBER_ID, user_id=user.id, team_id=team.id, role=TeamRole.MANAGER
    )
    team_repo.get_team_for_user.return_value = team
    team_member_repo.update_member_role.return_value = promoted
    team_member_repo.get_member_by_team_and_user_id.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.update_member_role(data, manager)

    team_repo.update_team_manager.assert_not_awaited()


async def test_update_member_role_manager_assigning_self_is_not_demoted(
    service, team_repo, team_member_repo, manager, team
):
    manager_member = SimpleNamespace(
        id=MANAGER_MEMBER_ID,
        user_id=manager.id,
        team_id=team.id,
        role=TeamRole.MANAGER,
    )
    data = TeamMemberUpdate(
        id=MANAGER_MEMBER_ID, team_id=team.id, role=TeamRole.MANAGER
    )
    team_repo.get_team_for_user.return_value = team
    team_member_repo.update_member_role.return_value = manager_member
    team_member_repo.get_member_by_id.return_value = manager_member

    result = await service.update_member_role(data, manager)

    assert result is manager_member
    team_member_repo.update_member_role.assert_awaited_once_with(member=data)
    team_member_repo.get_member_by_team_and_user_id.assert_not_awaited()
    team_repo.update_team_manager.assert_not_awaited()


# --- remove_member ----------------------------------------------------------


async def test_remove_member(
    service, team_repo, team_member_repo, manager, team, member
):
    team_repo.get_team_for_user.return_value = team
    team_member_repo.get_member_by_team_and_user_id.return_value = member
    team_member_repo.remove_member.return_value = True

    result = await service.remove_member(team.id, USER_ID, manager)

    assert result is None
    team_repo.get_team_for_user.assert_awaited_once_with(team.id, manager.id)
    team_member_repo.get_member_by_team_and_user_id.assert_awaited_once_with(
        team.id, USER_ID
    )
    team_member_repo.remove_member.assert_awaited_once_with(
        user_id=USER_ID, team_id=team.id
    )


async def test_remove_member_team_not_found(
    service, team_repo, team_member_repo, manager
):
    team_repo.get_team_for_user.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.remove_member(10, USER_ID, manager)

    team_member_repo.remove_member.assert_not_awaited()


async def test_remove_member_by_non_manager(
    service, team_repo, team_member_repo, stranger, team
):
    team_repo.get_team_for_user.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.remove_member(team.id, USER_ID, stranger)

    team_member_repo.remove_member.assert_not_awaited()


async def test_remove_member_not_found(
    service, team_repo, team_member_repo, manager, team
):
    team_repo.get_team_for_user.return_value = team
    team_member_repo.get_member_by_team_and_user_id.return_value = None

    with pytest.raises(TeamMemberNotFoundError):
        await service.remove_member(team.id, USER_ID, manager)

    team_member_repo.remove_member.assert_not_awaited()


@pytest.mark.parametrize("role", [TeamRole.MANAGER, TeamRole.ADMIN])
async def test_remove_member_cannot_remove_manager_or_admin(
    service, team_repo, team_member_repo, manager, team, role
):
    privileged = SimpleNamespace(
        id=MEMBER_ID, user_id=USER_ID, team_id=team.id, role=role
    )
    team_repo.get_team_for_user.return_value = team
    team_member_repo.get_member_by_team_and_user_id.return_value = privileged

    with pytest.raises(CannotRemoveManagerError):
        await service.remove_member(team.id, USER_ID, manager)

    team_member_repo.remove_member.assert_not_awaited()


async def test_remove_member_repository_removed_nothing(
    service, team_repo, team_member_repo, manager, team, member
):
    team_repo.get_team_for_user.return_value = team
    team_member_repo.get_member_by_team_and_user_id.return_value = member
    team_member_repo.remove_member.return_value = False

    with pytest.raises(TeamMemberNotFoundError):
        await service.remove_member(team.id, USER_ID, manager)
