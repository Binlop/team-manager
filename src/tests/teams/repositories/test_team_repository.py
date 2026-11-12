import pytest
from sqlalchemy import select

from teams.models import Team, TeamMember
from teams.repositories import TeamRepository
from teams.schemas import TeamCreate, TeamUpdate

pytestmark = pytest.mark.asyncio

MISSING_ID = 999_999


@pytest.fixture
def repository(uow):
    return TeamRepository(uow)


async def test_create_team(repository, make_user):
    manager = await make_user()

    team = await repository.create_team(
        TeamCreate(name="Alpha", invite_code="ALPHA1", manager_id=manager.id)
    )

    assert isinstance(team, Team)
    assert team.id is not None
    assert team.name == "Alpha"
    assert team.invite_code == "ALPHA1"
    assert team.manager_id == manager.id


async def test_create_team_adds_manager_as_member(repository, session, make_user, roles):
    manager = await make_user()

    team = await repository.create_team(
        TeamCreate(name="Alpha", invite_code="ALPHA1", manager_id=manager.id)
    )

    res = await session.execute(select(TeamMember).where(TeamMember.team_id == team.id))
    members = res.scalars().all()
    assert len(members) == 1
    assert members[0].user_id == manager.id
    assert members[0].role == roles.MANAGER


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


async def test_get_team_by_invite_code(repository, make_team):
    team = await make_team()
    await make_team()  # другая команда с другим кодом

    found = await repository.get_team_by_invite_code(team.invite_code)

    assert found is not None
    assert found.id == team.id


async def test_get_team_by_invite_code_not_found(repository):
    assert await repository.get_team_by_invite_code("no-such-code") is None


async def test_get_team_members(repository, make_team, make_user, make_member, detach):
    team = await make_team()
    other_team = await make_team()
    extra_user = await make_user()
    await make_member(extra_user, team)

    team_id, other_team_id = team.id, other_team.id
    expected_user_ids = {team.manager_id, extra_user.id}
    await detach()

    members = await repository.get_team_members(team_id)

    assert {m.user_id for m in members} == expected_user_ids
    assert all(m.team_id == team_id for m in members)
    assert other_team_id not in {m.team_id for m in members}
    # user и team подгружены через joinedload
    assert all(m.user.id == m.user_id for m in members)
    assert all(m.team.id == team_id for m in members)


async def test_get_team_members_empty(repository, make_team):
    team = await make_team(with_manager_member=False)

    assert await repository.get_team_members(team.id) == []


async def test_update_team(repository, make_team):
    team = await make_team()

    updated = await repository.update_team(
        team.id,
        TeamUpdate(name="Renamed", invite_code="ALPHA2"),
    )

    assert updated is not None
    assert updated.id == team.id
    assert updated.name == "Renamed"


async def test_update_team_not_found(repository):
    result = await repository.update_team(
        MISSING_ID,
        TeamUpdate(name="X", invite_code="XXXXXX"),
    )

    assert result is None