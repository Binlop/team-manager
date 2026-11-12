import pytest

from teams.models import Meeting, MeetingStatus, UserMeeting
from teams.repositories import MeetingRepository
from teams.schemas import MeetingCreate

pytestmark = pytest.mark.asyncio

MISSING_ID = 999_999


@pytest.fixture
def repository(uow):
    return MeetingRepository(uow)


# --- create_meeting ---------------------------------------------------------

async def test_create_meeting(repository, make_user, at):
    organizer = await make_user()

    meeting = await repository.create_meeting(
        MeetingCreate(
            name="Planning",
            starts_at=at(0),
            ends_at=at(1),
            status=MeetingStatus.SCHEDULED,
        ),
        user_id=organizer.id,
    )

    assert isinstance(meeting, Meeting)
    assert meeting.id is not None
    assert meeting.name == "Planning"
    assert meeting.starts_at == at(0)
    assert meeting.ends_at == at(1)
    assert meeting.status == MeetingStatus.SCHEDULED
    assert meeting.organizer_id == organizer.id


# --- add_user_to_meeting ----------------------------------------------------

async def test_add_user_to_meeting(repository, make_user, make_meeting):
    user = await make_user()
    meeting = await make_meeting()

    user_meeting = await repository.add_user_to_meeting(meeting.id, user.id)

    assert isinstance(user_meeting, UserMeeting)
    assert user_meeting.id is not None
    assert user_meeting.user_id == user.id
    assert user_meeting.meeting_id == meeting.id


# --- get_meeting_by_id ------------------------------------------------------

async def test_get_meeting_by_id_for_participant(
    repository, make_user, make_meeting, detach
):
    organizer = await make_user()
    participant = await make_user()
    meeting = await make_meeting(organizer=organizer, participants=(organizer, participant))
    meeting_id, organizer_id, participant_id = meeting.id, organizer.id, participant.id
    await detach()

    found = await repository.get_meeting_by_id(meeting_id, participant_id)

    assert found is not None
    assert found.id == meeting_id
    # organizer и users подгружены
    assert found.organizer.id == organizer_id
    assert {u.id for u in found.users} == {organizer_id, participant_id}


async def test_get_meeting_by_id_for_non_participant(repository, make_user, make_meeting):
    participant = await make_user()
    stranger = await make_user()
    meeting = await make_meeting(participants=(participant,))

    assert await repository.get_meeting_by_id(meeting.id, stranger.id) is None


async def test_get_meeting_by_id_not_found(repository, make_user):
    user = await make_user()

    assert await repository.get_meeting_by_id(MISSING_ID, user.id) is None


# --- get_user_meetings ------------------------------------------------------

async def test_get_user_meetings_returns_only_users_scheduled(
    repository, make_user, make_meeting, other_status, detach
):
    user = await make_user()
    someone = await make_user()

    mine_1 = await make_meeting(start_h=0, end_h=1, participants=(user,))
    mine_2 = await make_meeting(start_h=5, end_h=6, participants=(user, someone))
    await make_meeting(start_h=0, end_h=1, participants=(someone,))  # чужая
    await make_meeting(  # моя, но не SCHEDULED
        start_h=10, end_h=11, status=other_status, participants=(user,)
    )
    expected_ids = {mine_1.id, mine_2.id}
    user_id = user.id
    await detach()

    meetings = await repository.get_user_meetings(user_id)

    assert {m.id for m in meetings} == expected_ids
    # связи подгружены
    for m in meetings:
        assert m.organizer.id == m.organizer_id
        assert user_id in {u.id for u in m.users}


async def test_get_user_meetings_empty(repository, make_user):
    user = await make_user()

    assert await repository.get_user_meetings(user.id) == []


# --- check_user_meeting_conflicts ------------------------------------------
# Существующая встреча: 0 - 1 (часы от T0).

@pytest.mark.parametrize(
    "start_h, end_h, expected",
    [
        (-1, 0.5, True),     # пересекается с началом
        (0.5, 2, True),      # пересекается с концом
        (0.25, 0.75, True),  # внутри существующей
        (-1, 2, True),       # накрывает существующую
        (0, 1, True),        # совпадает
        (-1, 0, False),      # заканчивается ровно в момент старта
        (1, 2, False),       # начинается ровно в момент конца
        (-3, -2, False),     # раньше
        (2, 3, False),       # позже
    ],
)
async def test_check_user_meeting_conflicts(
    repository, make_user, make_meeting, at, start_h, end_h, expected
):
    user = await make_user()
    await make_meeting(start_h=0, end_h=1, participants=(user,))

    result = await repository.check_user_meeting_conflicts(at(start_h), at(end_h), user.id)

    assert result is expected


async def test_check_user_meeting_conflicts_ignores_other_users(
    repository, make_user, make_meeting, at
):
    user = await make_user()
    someone = await make_user()
    await make_meeting(start_h=0, end_h=1, participants=(someone,))

    assert await repository.check_user_meeting_conflicts(at(0), at(1), user.id) is False


# --- get_user_meeting -------------------------------------------------------

async def test_get_user_meeting(repository, make_user, make_meeting, detach):
    user = await make_user()
    meeting = await make_meeting()
    user_meeting = await repository.add_user_to_meeting(meeting.id, user.id)
    um_id, user_id, meeting_id = user_meeting.id, user.id, meeting.id
    await detach()

    found = await repository.get_user_meeting(um_id)

    assert found is not None
    assert found.id == um_id
    assert found.user.id == user_id
    assert found.meeting.id == meeting_id


async def test_get_user_meeting_not_found(repository):
    assert await repository.get_user_meeting(MISSING_ID) is None


# --- get_user_meetings_in_time ---------------------------------------------
# Окно запроса: 1 - 3 (часы от T0).

async def test_get_user_meetings_in_time(repository, make_user, make_meeting, at, detach):
    user = await make_user()
    someone = await make_user()

    inside = await make_meeting(start_h=1, end_h=2, participants=(user,))
    overlapping = await make_meeting(start_h=2.5, end_h=4, participants=(user,))
    await make_meeting(start_h=0, end_h=1, participants=(user,))    # кончается в начале окна
    await make_meeting(start_h=3, end_h=5, participants=(user,))    # начинается в конце окна
    await make_meeting(start_h=1, end_h=2, participants=(someone,))  # в окне, но чужая
    await make_meeting(start_h=10, end_h=11, participants=(user,))   # далеко после окна
    expected_ids = {inside.id, overlapping.id}
    user_id = user.id
    await detach()

    meetings = await repository.get_user_meetings_in_time(at(1), at(3), user_id)

    assert {m.id for m in meetings} == expected_ids
    for m in meetings:
        assert m.organizer.id == m.organizer_id
        assert user_id in {u.id for u in m.users}


async def test_get_user_meetings_in_time_empty(repository, make_user, at):
    user = await make_user()

    assert await repository.get_user_meetings_in_time(at(0), at(1), user.id) == []