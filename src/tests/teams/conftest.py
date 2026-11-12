"""
Общие фикстуры для тестов репозиториев teams.

Положи файл в src/tests/teams/conftest.py.
Использует фикстуры из корневого conftest: session, uow, user_factory.
"""
import itertools
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from teams.models import Meeting, MeetingStatus, Team, TeamMember, TeamRole, UserMeeting

ROLE_MANAGER = TeamRole.MANAGER
ROLE_MEMBER = TeamRole.MEMBER

# Naive datetime: SQLite всё равно не хранит tzinfo.
T0 = datetime(2030, 1, 1, 10, 0)

_counter = itertools.count(1)


@pytest.fixture
def roles():
    return SimpleNamespace(MANAGER=ROLE_MANAGER, MEMBER=ROLE_MEMBER)


@pytest.fixture
def at():
    """at(1.5) -> T0 + 1.5 часа."""

    def _at(hours: float) -> datetime:
        return T0 + timedelta(hours=hours)

    return _at


@pytest.fixture
def detach(session):
    """
    Сбрасывает identity map, чтобы репозиторий загрузил объекты заново.
    Так проверяется, что joinedload/selectinload действительно подгрузили
    связи: в async-сессии ленивая загрузка бросила бы MissingGreenlet.
    """

    async def _detach() -> None:
        await session.flush()
        session.expunge_all()

    return _detach


@pytest.fixture
def make_user(user_factory):
    """user_factory с уникальными username/email (дефолты у него одинаковые)."""

    async def _make():
        n = next(_counter)
        return await user_factory(username=f"user{n}", email=f"user{n}@example.com")

    return _make


@pytest.fixture
def make_team(session, make_user):
    """Создаёт команду напрямую через модели (без репозитория)."""

    async def _make(manager=None, with_manager_member: bool = True) -> Team:
        manager = manager or await make_user()
        n = next(_counter)
        team = Team(
            name=f"Team {n}",
            invite_code=f"invite-{n}",
            manager_id=manager.id,
        )
        session.add(team)
        await session.flush()
        if with_manager_member:
            session.add(
                TeamMember(user_id=manager.id, team_id=team.id, role=ROLE_MANAGER)
            )
            await session.flush()
        return team

    return _make


@pytest.fixture
def make_member(session):
    async def _make(user, team, role=ROLE_MEMBER) -> TeamMember:
        member = TeamMember(user_id=user.id, team_id=team.id, role=role)
        session.add(member)
        await session.flush()
        return member

    return _make


@pytest.fixture
def make_meeting(session, make_user, at):
    """Время задаётся в часах от T0: start_h=0, end_h=1 -> 10:00-11:00."""

    async def _make(
        organizer=None,
        start_h: float = 0,
        end_h: float = 1,
        status: MeetingStatus = MeetingStatus.SCHEDULED,
        participants: tuple = (),
    ) -> Meeting:
        organizer = organizer or await make_user()
        meeting = Meeting(
            name=f"Meeting {next(_counter)}",
            starts_at=at(start_h),
            ends_at=at(end_h),
            status=status,
            organizer_id=organizer.id,
        )
        session.add(meeting)
        await session.flush()
        for user in participants:
            session.add(UserMeeting(user_id=user.id, meeting_id=meeting.id))
        await session.flush()
        return meeting

    return _make


@pytest.fixture
def other_status():
    """Любой статус встречи, отличный от SCHEDULED."""
    others = [s for s in MeetingStatus if s != MeetingStatus.SCHEDULED]
    if not others:
        pytest.skip("В MeetingStatus нет статусов кроме SCHEDULED")
    return others[0]