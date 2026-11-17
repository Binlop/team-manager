import pytest
from sqlalchemy import select

from teams.models import Team, TeamMember, TeamRole
from teams.repositories import TeamRepository
from teams.schemas import TeamBase, TeamUpdate

pytestmark = pytest.mark.asyncio

MISSING_ID = 999_999


@pytest.fixture
def repository(uow):
    return TeamRepository(uow)


# --- create_team ------------------------------------------------------------


async def test_create_team(repository, make_user):
    manager = await make_user()

    team = await repository.create_team(
        TeamBase(name="Alpha"),
        user_id=manager.id,
        invite_code="hashed-invite-code",
    )

    assert isinstance(team, Team)
    assert team.id is not None
    assert team.name == "Alpha"
    assert team.invite_code == "hashed-invite-code"
    assert team.manager_id == manager.id


async def test_create_team_adds_manager_as_team_member(repository, session, make_user):
    manager = await make_user()

    team = await repository.create_team(
        TeamBase(name="Alpha"),
        user_id=manager.id,
        invite_code="hashed-invite-code",
    )

    result = await session.execute(
        select(TeamMember).where(TeamMember.team_id == team.id)
    )
    members = result.scalars().all()

    assert len(members) == 1
    assert members[0].user_id == manager.id
    assert members[0].team_id == team.id
    assert members[0].role == TeamRole.MANAGER


async def test_create_team_allows_same_name_for_different_managers(
    repository, make_user
):
    first_manager = await make_user()
    second_manager = await make_user()

    first = await repository.create_team(
        TeamBase(name="Same name"),
        user_id=first_manager.id,
        invite_code="code-1",
    )
    second = await repository.create_team(
        TeamBase(name="Same name"),
        user_id=second_manager.id,
        invite_code="code-2",
    )

    assert first.id != second.id
    assert first.name == second.name == "Same name"


# --- get_team_by_id ---------------------------------------------------------


async def test_get_team_by_id(repository, make_team, detach):
    team = await make_team()
    team_id, manager_id = team.id, team.manager_id
    await detach()

    found = await repository.get_team_by_id(team_id)

    assert found is not None
    assert found.id == team_id
    # manager подгружен через joinedload (иначе MissingGreenlet)
    assert found.manager.id == manager_id


async def test_get_team_by_id_not_found(repository):
    assert await repository.get_team_by_id(MISSING_ID) is None


# --- get_team_for_user ------------------------------------------------------


async def test_get_team_for_user_as_manager(repository, make_team, detach):
    # Менеджеру доступ есть даже без записи в team_member.
    team = await make_team(with_manager_member=False)
    team_id, manager_id = team.id, team.manager_id
    await detach()

    found = await repository.get_team_for_user(team_id, manager_id)

    assert found is not None
    assert found.id == team_id
    assert found.manager.id == manager_id


async def test_get_team_for_user_as_member(
    repository, make_team, make_user, make_member, detach
):
    team = await make_team(with_manager_member=False)
    member = await make_user()
    await make_member(member, team)
    team_id, member_id = team.id, member.id
    await detach()

    found = await repository.get_team_for_user(team_id, member_id)

    assert found is not None
    assert found.id == team_id


async def test_get_team_for_user_as_stranger(
    repository, make_team, make_user
):
    team = await make_team()
    stranger = await make_user()

    assert await repository.get_team_for_user(team.id, stranger.id) is None


async def test_get_team_for_user_not_found(repository, make_user):
    user = await make_user()

    assert await repository.get_team_for_user(MISSING_ID, user.id) is None


async def test_get_team_for_user_does_not_leak_other_teams(
    repository, make_team, detach
):
    first_team = await make_team()
    second_team = await make_team()
    first_team_id, second_team_manager_id = first_team.id, second_team.manager_id
    await detach()

    # Менеджер второй команды не должен получить доступ к первой.
    found = await repository.get_team_for_user(first_team_id, second_team_manager_id)

    assert found is None


# --- get_team_by_invite_code ------------------------------------------------


async def test_get_team_by_invite_code(repository, make_team):
    team = await make_team()
    await make_team()

    found = await repository.get_team_by_invite_code(team.invite_code)

    assert found is not None
    assert found.id == team.id


async def test_get_team_by_invite_code_not_found(repository):
    assert await repository.get_team_by_invite_code("no-such-code") is None


# --- get_team_members -------------------------------------------------------


async def test_get_team_members(repository, make_team, make_user, make_member, detach):
    team = await make_team()
    other_team = await make_team()
    extra_user = await make_user()
    await make_member(extra_user, team)

    team_id, other_team_id = team.id, other_team.id
    expected_user_ids = {team.manager_id, extra_user.id}
    observer_id = team.manager_id
    await detach()

    members = await repository.get_team_members(team_id, observer_id)

    assert {m.user_id for m in members} == expected_user_ids
    assert all(m.team_id == team_id for m in members)
    assert other_team_id not in {m.team_id for m in members}
    # user и team подгружены через joinedload
    assert all(m.user.id == m.user_id for m in members)
    assert all(m.team.id == team_id for m in members)


async def test_get_team_members_for_stranger_returns_empty_list(
    repository, make_team, make_user
):
    team = await make_team()
    stranger = await make_user()

    assert await repository.get_team_members(team.id, stranger.id) == []


async def test_get_team_members_empty_for_manager_without_membership(
    repository, make_team, detach
):
    # get_team_members фильтрует по участию в team_member, а не по manager_id.
    team = await make_team(with_manager_member=False)
    team_id, manager_id = team.id, team.manager_id
    await detach()

    assert await repository.get_team_members(team_id, manager_id) == []


# --- update_team ------------------------------------------------------------


async def test_update_team(repository, make_team, detach):
    team = await make_team()
    team_id, manager_id = team.id, team.manager_id
    await detach()

    updated = await repository.update_team(
        team_id,
        TeamUpdate(id=team_id, name="Renamed"),
        manager_id,
    )

    assert updated is not None
    assert updated.id == team_id
    assert updated.name == "Renamed"


async def test_update_team_does_not_change_invite_code(
    repository, make_team, detach
):
    team = await make_team()
    team_id, manager_id, invite_code = team.id, team.manager_id, team.invite_code
    await detach()

    await repository.update_team(
        team_id,
        TeamUpdate(id=team_id, name="Renamed"),
        manager_id,
    )

    found = await repository.get_team_by_id(team_id)
    assert found is not None
    assert found.invite_code == invite_code


async def test_update_team_by_non_manager(repository, make_team, make_user, detach):
    team = await make_team()
    stranger = await make_user()
    team_id, stranger_id = team.id, stranger.id
    await detach()

    result = await repository.update_team(
        team_id,
        TeamUpdate(id=team_id, name="Hacked"),
        stranger_id,
    )

    assert result is None
    found = await repository.get_team_by_id(team_id)
    assert found is not None
    assert found.name != "Hacked"


async def test_update_team_not_found(repository, make_user):
    user = await make_user()

    result = await repository.update_team(
        MISSING_ID,
        TeamUpdate(id=MISSING_ID, name="X"),
        user.id,
    )

    assert result is None


# --- update_invite_code_team ------------------------------------------------


async def test_update_invite_code_team(repository, make_team, detach):
    team = await make_team()
    team_id, manager_id = team.id, team.manager_id
    await detach()

    updated = await repository.update_invite_code_team(
        team_id,
        "new-hashed-code",
        manager_id,
    )

    assert updated is not None
    assert updated.id == team_id
    assert updated.invite_code == "new-hashed-code"


async def test_update_invite_code_team_by_non_manager(
    repository, make_team, make_user, detach
):
    team = await make_team()
    stranger = await make_user()
    team_id, stranger_id, old_code = team.id, stranger.id, team.invite_code
    await detach()

    result = await repository.update_invite_code_team(
        team_id,
        "hacked-code",
        stranger_id,
    )

    assert result is None
    found = await repository.get_team_by_id(team_id)
    assert found is not None
    assert found.invite_code == old_code


async def test_update_invite_code_team_not_found(repository, make_user):
    user = await make_user()

    assert (
        await repository.update_invite_code_team(MISSING_ID, "code", user.id)
        is None
    )


# --- update_team_manager ----------------------------------------------------


async def test_update_team_manager(repository, make_team, make_user, detach):
    team = await make_team()
    new_manager = await make_user()
    team_id, new_manager_id = team.id, new_manager.id
    await detach()

    updated = await repository.update_team_manager(team_id, new_manager_id)

    assert updated is not None
    assert updated.id == team_id
    assert updated.manager_id == new_manager_id


async def test_update_team_manager_not_found(repository, make_user):
    user = await make_user()

    assert await repository.update_team_manager(MISSING_ID, user.id) is None
