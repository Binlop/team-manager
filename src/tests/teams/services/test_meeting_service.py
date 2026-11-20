from datetime import datetime
from types import SimpleNamespace

import pytest

from auth.exceptions import UserNotFoundError
from core.exceptions import PermissionDeniedError
from teams import exceptions
from teams.exceptions import MeetingNotFoundError
from teams.models import MeetingStatus
from teams.schemas import MeetingCreate, MeetingUpdate, UserMeetingCreate
from teams.services import MeetingService

pytestmark = pytest.mark.asyncio

PARTICIPANT_ID = 7
MISSING_ID = 999_999
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
        id=1,
        organizer_id=organizer.id,
        starts_at=STARTS_AT,
        ends_at=ENDS_AT,
        users=[],
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
    meeting_repo.check_user_meeting_conflicts.return_value = False
    meeting_repo.create_meeting.return_value = meeting
    meeting_repo.get_meeting_by_id.return_value = meeting

    result = await service.create_meeting(create_data, organizer)

    assert result is meeting
    meeting_repo.check_user_meeting_conflicts.assert_awaited_once_with(
        create_data.starts_at, create_data.ends_at, organizer.id
    )
    meeting_repo.create_meeting.assert_awaited_once_with(create_data, organizer.id)

    meeting_repo.add_user_to_meeting.assert_awaited_once_with(meeting.id, organizer.id)
    meeting_repo.get_meeting_by_id.assert_awaited_once_with(meeting.id, organizer.id)

async def test_create_meeting_time_conflict(service, meeting_repo, create_data, organizer):
    meeting_repo.check_user_meeting_conflicts.return_value = True

    with pytest.raises(exceptions.MeetingTimeConflictError):
        await service.create_meeting(create_data, organizer)

    meeting_repo.create_meeting.assert_not_awaited()
    meeting_repo.add_user_to_meeting.assert_not_awaited()


async def test_create_meeting_not_found_after_creation(
    service, meeting_repo, create_data, organizer, meeting
):
    meeting_repo.check_user_meeting_conflicts.return_value = False  # добавить
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

    with pytest.raises(exceptions.ParticipantTimeConflictError):
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


# --- update_meeting ---------------------------------------------------------


@pytest.fixture
def update_data(meeting):
    return MeetingUpdate(
        id=meeting.id,
        name="Rescheduled",
        starts_at=STARTS_AT,
        ends_at=ENDS_AT,
        status=MeetingStatus.CANCELLED,
    )


async def test_update_meeting(
    service, meeting_repo, organizer, meeting, update_data
):
    updated = SimpleNamespace(id=meeting.id)
    user_meeting = SimpleNamespace(id=50, user_id=organizer.id, meeting_id=meeting.id)
    meeting_repo.get_meeting_by_id.side_effect = [meeting, user_meeting]
    meeting_repo.update_meeting.return_value = updated

    result = await service.update_meeting(update_data, organizer)

    assert result is user_meeting
    assert meeting_repo.get_meeting_by_id.await_count == 2
    meeting_repo.get_meeting_by_id.assert_any_await(meeting.id, organizer.id)
    meeting_repo.update_meeting.assert_awaited_once_with(update_data)


async def test_update_meeting_not_found(
    service, meeting_repo, organizer, update_data
):
    meeting_repo.get_meeting_by_id.return_value = None

    with pytest.raises(MeetingNotFoundError):
        await service.update_meeting(update_data, organizer)

    meeting_repo.update_meeting.assert_not_awaited()


async def test_update_meeting_by_non_organizer(
    service, meeting_repo, stranger, meeting, update_data
):
    # stranger видит встречу (например, как участник), но не организатор.
    meeting_repo.get_meeting_by_id.return_value = meeting

    with pytest.raises(PermissionDeniedError):
        await service.update_meeting(update_data, stranger)

    meeting_repo.update_meeting.assert_not_awaited()


async def test_update_meeting_repository_did_not_update(
    service, meeting_repo, organizer, meeting, update_data
):
    meeting_repo.get_meeting_by_id.return_value = meeting
    meeting_repo.update_meeting.return_value = None

    with pytest.raises(MeetingNotFoundError):
        await service.update_meeting(update_data, organizer)


async def test_update_meeting_not_found_after_update(
    service, meeting_repo, organizer, meeting, update_data
):
    meeting_repo.get_meeting_by_id.side_effect = [meeting, None]
    meeting_repo.update_meeting.return_value = SimpleNamespace(id=meeting.id)

    with pytest.raises(exceptions.UserMeetingNotFoundError):
        await service.update_meeting(update_data, organizer)


# --- delete_meeting ---------------------------------------------------------


async def test_delete_meeting(service, meeting_repo, organizer, meeting):
    meeting_repo.get_meeting_by_id.return_value = meeting
    meeting_repo.delete_meeting.return_value = True

    result = await service.delete_meeting(meeting.id, organizer)

    assert result is None
    meeting_repo.get_meeting_by_id.assert_awaited_once_with(
        meeting.id, organizer.id
    )
    meeting_repo.delete_meeting.assert_awaited_once_with(meeting.id, organizer.id)


async def test_delete_meeting_not_found(service, meeting_repo, organizer):
    meeting_repo.get_meeting_by_id.return_value = None

    with pytest.raises(MeetingNotFoundError):
        await service.delete_meeting(MISSING_ID, organizer)

    meeting_repo.delete_meeting.assert_not_awaited()


async def test_delete_meeting_by_non_organizer(
    service, meeting_repo, stranger, meeting
):
    meeting_repo.get_meeting_by_id.return_value = meeting

    with pytest.raises(PermissionDeniedError):
        await service.delete_meeting(meeting.id, stranger)

    meeting_repo.delete_meeting.assert_not_awaited()


async def test_delete_meeting_repository_deleted_nothing(
    service, meeting_repo, organizer, meeting
):
    meeting_repo.get_meeting_by_id.return_value = meeting
    meeting_repo.delete_meeting.return_value = False

    with pytest.raises(MeetingNotFoundError):
        await service.delete_meeting(meeting.id, organizer)

