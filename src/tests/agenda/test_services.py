from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from agenda.services import AgendaService


pytestmark = pytest.mark.asyncio


@pytest.fixture
def service():
    meeting_repo = AsyncMock()
    task_repo = AsyncMock()

    service = AgendaService(
        meeting_repo=meeting_repo,
        task_repo=task_repo,
    )

    return SimpleNamespace(
        service=service,
        meeting_repo=meeting_repo,
        task_repo=task_repo,
    )


@pytest.fixture
def user():
    return SimpleNamespace(id=1)


@pytest.fixture
def time_window():
    return (
        datetime(2030, 1, 1, 0, 0),
        datetime(2030, 1, 7, 23, 59),
    )


# ---------------------------------------------------------
# get_user_agends
# ---------------------------------------------------------

async def test_get_user_agends_success(
    service,
    user,
    time_window,
):
    starts_at, ends_at = time_window

    meetings = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]

    tasks = [
        SimpleNamespace(id=3),
        SimpleNamespace(id=4),
    ]

    service.meeting_repo.get_user_meetings_in_time.return_value = meetings
    service.task_repo.get_user_tasks_in_time.return_value = tasks

    result = await service.service.get_user_agends(
        starts_at,
        ends_at,
        user,
    )

    assert result == {
        "meetings": meetings,
        "tasks": tasks,
    }

    service.meeting_repo.get_user_meetings_in_time.assert_awaited_once_with(
        starts_at,
        ends_at,
        user.id,
    )

    service.task_repo.get_user_tasks_in_time.assert_awaited_once_with(
        starts_at,
        ends_at,
        user.id,
    )


async def test_get_user_agends_empty(
    service,
    user,
    time_window,
):
    starts_at, ends_at = time_window

    service.meeting_repo.get_user_meetings_in_time.return_value = []
    service.task_repo.get_user_tasks_in_time.return_value = []

    result = await service.service.get_user_agends(
        starts_at,
        ends_at,
        user,
    )

    assert result == {
        "meetings": [],
        "tasks": [],
    }


async def test_get_user_agends_only_meetings(
    service,
    user,
    time_window,
):
    starts_at, ends_at = time_window

    meetings = [SimpleNamespace(id=1)]

    service.meeting_repo.get_user_meetings_in_time.return_value = meetings
    service.task_repo.get_user_tasks_in_time.return_value = []

    result = await service.service.get_user_agends(
        starts_at,
        ends_at,
        user,
    )

    assert result == {
        "meetings": meetings,
        "tasks": [],
    }


async def test_get_user_agends_only_tasks(
    service,
    user,
    time_window,
):
    starts_at, ends_at = time_window

    tasks = [SimpleNamespace(id=1)]

    service.meeting_repo.get_user_meetings_in_time.return_value = []
    service.task_repo.get_user_tasks_in_time.return_value = tasks

    result = await service.service.get_user_agends(
        starts_at,
        ends_at,
        user,
    )

    assert result == {
        "meetings": [],
        "tasks": tasks,
    }