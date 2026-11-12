# tests/tasks/services/test_task_service.py

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.exceptions import PermissionDeniedError
from tasks.services import TaskService
from tasks.schemas import TaskCreate, TaskUpdate
from tasks.models import TaskStatus
from tasks.exceptions import AssigneeNotInTeamError, TaskNotFoundError
from teams.exceptions import TeamNotFoundError


pytestmark = pytest.mark.asyncio


@pytest.fixture
def service():
    task_repo = AsyncMock()
    team_repo = AsyncMock()
    team_member_repo = AsyncMock()

    service = TaskService(
        task_repo=task_repo,
        team_repo=team_repo,
        team_member_repo=team_member_repo,
    )

    return SimpleNamespace(
        service=service,
        task_repo=task_repo,
        team_repo=team_repo,
        team_member_repo=team_member_repo,
    )


@pytest.fixture
def user():
    return SimpleNamespace(id=1)


@pytest.fixture
def team():
    return SimpleNamespace(
        id=10,
        manager_id=1,
    )


@pytest.fixture
def task(team):
    return SimpleNamespace(
        id=100,
        team_id=team.id,
        team=team,
        assignee_id=2,
    )


@pytest.fixture
def create_task_data():
    return TaskCreate(
        title="Test task",
        description="Description",
        due_date=date(2030, 1, 10),
        assignee_id=2,
        team_id=10,
    )


@pytest.fixture
def update_task_data():
    return TaskUpdate(
        id=100,
        title="Updated task",
        description="Updated description",
        due_date=date(2030, 1, 10),
        assignee_id=2,
        team_id=10,
        manager_comment=None,
    )


# ---------------------------------------------------------
# get_task
# ---------------------------------------------------------

async def test_get_task_success(service, user, task):
    service.task_repo.get_task_by_id.return_value = task

    result = await service.service.get_task(task.id, user)

    assert result is task

    service.task_repo.get_task_by_id.assert_awaited_once_with(
        task.id,
        user.id,
    )


async def test_get_task_not_found(service, user):
    service.task_repo.get_task_by_id.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.service.get_task(100, user)

    service.task_repo.get_task_by_id.assert_awaited_once_with(
        100,
        user.id,
    )


# ---------------------------------------------------------
# get_team_tasks
# ---------------------------------------------------------

async def test_get_team_tasks(service, user, task):
    tasks = [task]
    service.task_repo.get_tasks_by_team_id.return_value = tasks

    result = await service.service.get_team_tasks(10, user)

    assert result == tasks

    service.task_repo.get_tasks_by_team_id.assert_awaited_once_with(
        10,
        user.id,
    )


# ---------------------------------------------------------
# get_user_tasks
# ---------------------------------------------------------

async def test_get_user_tasks(service, user, task):
    tasks = [task]
    service.task_repo.get_tasks_by_user_id.return_value = tasks

    result = await service.service.get_user_tasks(user)

    assert result == tasks

    service.task_repo.get_tasks_by_user_id.assert_awaited_once_with(
        user.id,
    )


# ---------------------------------------------------------
# get_mean_task_score
# ---------------------------------------------------------

async def test_get_mean_task_score(service, user):
    service.task_repo.get_mean_task_score_for_user.return_value = 4.5

    result = await service.service.get_mean_task_score(user)

    assert result == {"mean_score": 4.5}

    service.task_repo.get_mean_task_score_for_user.assert_awaited_once_with(
        user.id,
    )


async def test_get_mean_task_score_without_scores(service, user):
    service.task_repo.get_mean_task_score_for_user.return_value = None

    result = await service.service.get_mean_task_score(user)

    assert result == {"mean_score": None}


# ---------------------------------------------------------
# create_task
# ---------------------------------------------------------

async def test_create_task_success(
    service,
    user,
    team,
    create_task_data,
    task,
):
    created = SimpleNamespace(id=task.id)

    service.team_repo.get_team_by_id.return_value = team
    service.team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = True
    service.task_repo.create_task.return_value = created
    service.task_repo.get_task_by_id.return_value = task

    result = await service.service.create_task(create_task_data, user)

    assert result is task

    service.team_repo.get_team_by_id.assert_awaited_once_with(
        create_task_data.team_id,
    )

    service.team_member_repo.check_member_exists_with_user_id_and_team_id.assert_awaited_once_with(
        create_task_data.assignee_id,
        create_task_data.team_id,
    )

    service.task_repo.create_task.assert_awaited_once_with(
        data=create_task_data,
    )

    service.task_repo.get_task_by_id.assert_awaited_once_with(
        created.id,
        user.id,
    )


async def test_create_task_team_not_found(
    service,
    user,
    create_task_data,
):
    service.team_repo.get_team_by_id.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.service.create_task(create_task_data, user)

    service.task_repo.create_task.assert_not_awaited()
    service.team_member_repo.check_member_exists_with_user_id_and_team_id.assert_not_awaited()


async def test_create_task_user_is_not_manager(
    service,
    user,
    create_task_data,
):
    team = SimpleNamespace(
        id=create_task_data.team_id,
        manager_id=999,
    )

    service.team_repo.get_team_by_id.return_value = team

    with pytest.raises(PermissionDeniedError):
        await service.service.create_task(create_task_data, user)

    service.team_member_repo.check_member_exists_with_user_id_and_team_id.assert_not_awaited()
    service.task_repo.create_task.assert_not_awaited()


async def test_create_task_assignee_not_in_team(
    service,
    user,
    team,
    create_task_data,
):
    service.team_repo.get_team_by_id.return_value = team
    service.team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False

    with pytest.raises(AssigneeNotInTeamError):
        await service.service.create_task(create_task_data, user)

    service.task_repo.create_task.assert_not_awaited()


async def test_create_task_without_assignee(
    service,
    user,
    team,
    task,
):
    data = TaskCreate(
        title="Task without assignee",
        description="Description",
        due_date=date(2030, 1, 10),
        assignee_id=None,
        team_id=team.id,
    )

    created = SimpleNamespace(id=task.id)

    service.team_repo.get_team_by_id.return_value = team
    service.task_repo.create_task.return_value = created
    service.task_repo.get_task_by_id.return_value = task

    result = await service.service.create_task(data, user)

    assert result is task

    service.team_member_repo.check_member_exists_with_user_id_and_team_id.assert_not_awaited()


# ---------------------------------------------------------
# update_task
# ---------------------------------------------------------

async def test_update_task_by_manager(
    service,
    user,
    task,
    update_task_data,
):
    updated_task = SimpleNamespace(id=task.id)

    service.task_repo.get_task_by_id.side_effect = [
        task,
        task,
    ]
    service.task_repo.update_task.return_value = updated_task

    result = await service.service.update_task(update_task_data, user)

    assert result is task

    expected_payload = update_task_data.model_dump(
        exclude_unset=True,
        exclude={"id", "team_id"},
    )

    service.task_repo.update_task.assert_awaited_once_with(
        {"id": update_task_data.id, **expected_payload},
    )

    assert service.task_repo.get_task_by_id.await_count == 2


async def test_update_task_by_member(
    service,
    task,
    update_task_data,
):
    user = SimpleNamespace(id=2)

    task.team.manager_id = 1

    data = update_task_data.model_copy(
        update={"status": TaskStatus.OPEN},
    )

    service.task_repo.get_task_by_id.side_effect = [
        task,
        task,
    ]
    service.task_repo.update_task.return_value = SimpleNamespace(id=task.id)

    result = await service.service.update_task(data, user)

    assert result is task

    service.task_repo.update_task.assert_awaited_once_with({
        "id": data.id,
        "status": TaskStatus.OPEN,
    })


async def test_update_task_not_found(service, user, update_task_data):
    service.task_repo.get_task_by_id.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.service.update_task(update_task_data, user)

    service.task_repo.update_task.assert_not_awaited()


async def test_update_task_update_failed(
    service,
    user,
    task,
    update_task_data,
):
    service.task_repo.get_task_by_id.return_value = task
    service.task_repo.update_task.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.service.update_task(update_task_data, user)

    assert service.task_repo.get_task_by_id.await_count == 1


async def test_update_task_result_not_found(
    service,
    user,
    task,
    update_task_data,
):
    service.task_repo.get_task_by_id.side_effect = [
        task,
        None,
    ]
    service.task_repo.update_task.return_value = SimpleNamespace(id=task.id)

    with pytest.raises(TaskNotFoundError):
        await service.service.update_task(update_task_data, user)

    assert service.task_repo.get_task_by_id.await_count == 2