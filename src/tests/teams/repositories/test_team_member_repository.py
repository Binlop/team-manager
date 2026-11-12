import pytest

from teams.models import TeamMember
from teams.repositories import TeamMemberRepository
from teams.schemas import TeamMemberCreate, TeamMemberUpdate

pytestmark = pytest.mark.asyncio

MISSING_ID = 999_999
MISSING_TEAM_ID = 999_999


@pytest.fixture
def repository(uow):
    return TeamMemberRepository(uow)


# --- get_member_by_id -------------------------------------------------------

async def test_get_member_by_id(repository, make_team, make_user, make_member, detach):
    team = await make_team()
    user = await make_user()
    member = await make_member(user, team)
    member_id, user_id, team_id = member.id, user.id, team.id
    await detach()

    found = await repository.get_member_by_id(member_id)

    assert found is not None
    assert found.id == member_id
    # user и team подгружены через joinedload
    assert found.user.id == user_id
    assert found.team.id == team_id


async def test_get_member_by_id_not_found(repository):
    assert await repository.get_member_by_id(MISSING_ID) is None


# --- get_member_by_team_and_user_id ----------------------------------------

async def test_get_member_by_team_and_user_id(
    repository, make_team, make_user, make_member, detach
):
    team = await make_team()
    user = await make_user()
    member = await make_member(user, team)
    member_id, user_id, team_id = member.id, user.id, team.id
    await detach()

    found = await repository.get_member_by_team_and_user_id(team_id, user_id)

    assert found is not None
    assert found.id == member_id
    assert found.user.id == user_id
    assert found.team.id == team_id


async def test_get_member_by_team_and_user_id_wrong_team(
    repository, make_team, make_user, make_member
):
    team = await make_team()
    other_team = await make_team()
    user = await make_user()
    await make_member(user, team)

    assert await repository.get_member_by_team_and_user_id(other_team.id, user.id) is None


async def test_get_member_by_team_and_user_id_wrong_user(
    repository, make_team, make_user, make_member
):
    team = await make_team()
    user = await make_user()
    stranger = await make_user()
    await make_member(user, team)

    assert await repository.get_member_by_team_and_user_id(team.id, stranger.id) is None


# --- check_member_exists_with_user_id_and_team_id --------------------------

async def test_check_member_exists_true(repository, make_team, make_user, make_member):
    team = await make_team()
    user = await make_user()
    await make_member(user, team)

    result = await repository.check_member_exists_with_user_id_and_team_id(user.id, team.id)

    assert result is True


async def test_check_member_exists_false_for_other_team(
    repository, make_team, make_user, make_member
):
    team = await make_team()
    other_team = await make_team()
    user = await make_user()
    await make_member(user, team)

    result = await repository.check_member_exists_with_user_id_and_team_id(
        user.id, other_team.id
    )

    assert result is False


async def test_check_member_exists_false_for_unknown(repository):
    result = await repository.check_member_exists_with_user_id_and_team_id(
        MISSING_ID, MISSING_ID
    )

    assert result is False


# --- add_team_member --------------------------------------------------------

async def test_add_team_member(repository, make_team, make_user, roles):
    team = await make_team()
    user = await make_user()

    member = await repository.add_team_member(
        TeamMemberCreate(user_id=user.id, team_id=team.id, role=roles.MEMBER)
    )

    assert isinstance(member, TeamMember)
    assert member.id is not None
    assert member.user_id == user.id
    assert member.team_id == team.id
    assert member.role == roles.MEMBER


# --- remove_member ----------------------------------------------------------

async def test_remove_member(repository, make_team, make_user, make_member):
    team = await make_team()
    user = await make_user()
    await make_member(user, team)

    removed = await repository.remove_member(user.id, team.id)

    assert removed is True
    assert await repository.check_member_exists_with_user_id_and_team_id(
        user.id, team.id
    ) is False


async def test_remove_member_not_found(repository, make_team, make_user):
    team = await make_team()
    user = await make_user()

    assert await repository.remove_member(user.id, team.id) is False


async def test_remove_member_keeps_membership_in_other_teams(
    repository, make_team, make_user, make_member
):
    team = await make_team()
    other_team = await make_team()
    user = await make_user()
    await make_member(user, team)
    await make_member(user, other_team)

    await repository.remove_member(user.id, team.id)

    assert await repository.check_member_exists_with_user_id_and_team_id(
        user.id, other_team.id
    ) is True


# --- update_member_role -----------------------------------------------------

async def test_update_member_role(repository, make_team, make_user, make_member, roles):
    team = await make_team()
    user = await make_user()
    member = await make_member(user, team, role=roles.MEMBER)

    updated = await repository.update_member_role(
        TeamMemberUpdate(id=member.id, team_id=team.id, role=roles.MANAGER)
    )

    assert updated is not None
    assert updated.id == member.id
    assert updated.role == roles.MANAGER


async def test_update_member_role_not_found(repository, roles):
    result = await repository.update_member_role(
        TeamMemberUpdate(id=MISSING_ID, team_id=MISSING_TEAM_ID, role=roles.MANAGER)
    )

    assert result is None