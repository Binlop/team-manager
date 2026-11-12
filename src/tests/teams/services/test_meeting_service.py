from datetime import datetime
from types import SimpleNamespace

import pytest

from auth.exceptions import UserNotFoundError
from core.exceptions import PermissionDeniedError
from teams import exceptions
from teams.exceptions import MeetingNotFoundError
from teams.models import MeetingStatus
from teams.schemas import MeetingCreate, UserMeetingCreate
from teams.services import MeetingService

pytestmark = pytest.mark.asyncio

PARTICIPANT_ID = 7
STARTS_AT = datetime(2030, 1, 1, 10, 0)
ENDS_AT = datetime(2030, 1, 1, 11, 0)


@pytest.fixture
def service(meeting_repo, user_repo):
    return MeetingService(meeting_repo=meeting_repo, user_repo=user_repo)


@pytest.fixture
def organizer(manager):
    """Организатор встречи (тот же пользователь, что и manager в conftest)."""
    return manager


@pytest.fixture
def meeting(organizer):
    return SimpleNamespace(
        id=1, organizer_id=organizer.id, starts_at=STARTS_AT, ends_at=ENDS_AT
    )


# --- create_meeting ---------------------------------------------------------

@pytest.fixture
def create_data():
    return MeetingCreate(
        name="Planning",
        starts_at=STARTS_AT,
        ends_at=ENDS_AT,
        status=MeetingStatus.SCHEDULED,
    )


async def test_create_meeting(service, meeting_repo, create_data, organizer, meeting):
    meeting_repo.create_meeting.return_value = meeting
    meeting_repo.get_meeting_by_id.return_value = meeting

    result = await service.create_meeting(create_data, organizer)

    assert result is meeting
    meeting_repo.create_meeting.assert_awaited_once_with(create_data, organizer.id)
    # организатор автоматически становится участником
    meeting_repo.add_user_to_meeting.assert_awaited_once_with(meeting.id, organizer.id)
    meeting_repo.get_meeting_by_id.assert_awaited_once_with(meeting.id, organizer.id)


async def test_create_meeting_not_found_after_creation(
    service, meeting_repo, create_data, organizer, meeting
):
    meeting_repo.create_meeting.return_value = meeting
    meeting_repo.get_meeting_by_id.return_value = None

    with pytest.raises(MeetingNotFoundError):
        await service.create_meeting(create_data, organizer)


# --- add_user_to_meeting ----------------------------------------------------

@pytest.fixture
def add_data(meeting):
    return UserMeetingCreate(meeting_id=meeting.id, participant_id=PARTICIPANT_ID)


@pytest.fixture
def happy_path(meeting_repo, user_repo, meeting):
    """Настраивает моки на успешное добавление участника."""
    user_meeting = SimpleNamespace(id=50, user_id=PARTICIPANT_ID, meeting_id=meeting.id)
    meeting_repo.get_meeting_by_id.return_value = meeting
    user_repo.check_user_exists.return_value = True
    meeting_repo.check_user_meeting_conflicts.return_value = False
    meeting_repo.add_user_to_meeting.return_value = SimpleNamespace(id=user_meeting.id)
    meeting_repo.get_user_meeting.return_value = user_meeting
    return user_meeting


async def test_add_user_to_meeting(
    service, meeting_repo, add_data, organizer, meeting, happy_path
):
    result = await service.add_user_to_meeting(add_data, organizer)

    assert result is happy_path
    meeting_repo.get_meeting_by_id.assert_awaited_once_with(meeting.id, organizer.id)
    meeting_repo.add_user_to_meeting.assert_awaited_once_with(meeting.id, PARTICIPANT_ID)
    meeting_repo.get_user_meeting.assert_awaited_once_with(happy_path.id)


async def test_add_user_to_meeting_meeting_not_found(
    service, meeting_repo, add_data, organizer
):
    meeting_repo.get_meeting_by_id.return_value = None

    with pytest.raises(MeetingNotFoundError):
        await service.add_user_to_meeting(add_data, organizer)

    meeting_repo.add_user_to_meeting.assert_not_awaited()


async def test_add_user_to_meeting_by_non_organizer(
    service, meeting_repo, add_data, stranger, happy_path
):
    # stranger видит встречу (участник), но не является организатором
    with pytest.raises(PermissionDeniedError):
        await service.add_user_to_meeting(add_data, stranger)

    meeting_repo.add_user_to_meeting.assert_not_awaited()


async def test_add_user_to_meeting_participant_not_found(
    service, meeting_repo, user_repo, add_data, organizer, happy_path
):
    user_repo.check_user_exists.return_value = False

    with pytest.raises(UserNotFoundError):
        await service.add_user_to_meeting(add_data, organizer)

    meeting_repo.add_user_to_meeting.assert_not_awaited()


async def test_add_user_to_meeting_awaits_participant_check(
    service, user_repo, add_data, organizer, happy_path
):
    await service.add_user_to_meeting(add_data, organizer)

    user_repo.check_user_exists.assert_awaited_once_with(PARTICIPANT_ID)


async def test_add_user_to_meeting_time_conflict(
    service, meeting_repo, add_data, organizer, happy_path
):
    meeting_repo.check_user_meeting_conflicts.return_value = True

    with pytest.raises(exceptions.MeetingTimeConflictError):
        await service.add_user_to_meeting(add_data, organizer)

    meeting_repo.add_user_to_meeting.assert_not_awaited()


async def test_add_user_to_meeting_checks_conflicts_for_participant(
    service, meeting_repo, add_data, organizer, meeting, happy_path
):
    await service.add_user_to_meeting(add_data, organizer)

    meeting_repo.check_user_meeting_conflicts.assert_awaited_once_with(
        meeting.starts_at, meeting.ends_at, PARTICIPANT_ID
    )


async def test_add_user_to_meeting_user_meeting_not_found_after_creation(
    service, meeting_repo, add_data, organizer, happy_path
):
    meeting_repo.get_user_meeting.return_value = None

    with pytest.raises(exceptions.UserMeetingNotFoundError):
        await service.add_user_to_meeting(add_data, organizer)


# --- get_user_meetings ------------------------------------------------------

async def test_get_user_meetings(service, meeting_repo, organizer):
    meetings = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    meeting_repo.get_user_meetings.return_value = meetings

    result = await service.get_user_meetings(organizer)

    assert result == meetings
    meeting_repo.get_user_meetings.assert_awaited_once_with(organizer.id)


# --- get_calendar_events ----------------------------------------------------

async def test_get_calendar_events_queries_meetings_in_range(
    service, meeting_repo, organizer
):
    meeting_repo.get_user_meetings_in_time.return_value = []

    await service.get_calendar_events(STARTS_AT, ENDS_AT, organizer)

    meeting_repo.get_user_meetings_in_time.assert_awaited_with(
        STARTS_AT, ENDS_AT, organizer.id
    )


@pytest.mark.xfail(
    reason="get_calendar_events ничего не возвращает (нет return), "
    "метод выглядит недописанным: переменная tasks дублирует meetings.",
)
async def test_get_calendar_events_returns_meetings(service, meeting_repo, organizer):
    meetings = [SimpleNamespace(id=1)]
    meeting_repo.get_user_meetings_in_time.return_value = meetings

    result = await service.get_calendar_events(STARTS_AT, ENDS_AT, organizer)

    assert result == meetings