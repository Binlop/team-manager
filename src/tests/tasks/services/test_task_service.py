from datetime import date
from types import SimpleNamespace
from unittest.mock import create_autospec

import pytest

from core.exceptions import PermissionDeniedError
from tasks.exceptions import AssigneeNotInTeamError, TaskNotFoundError
from tasks.models import TaskStatus
from tasks.repositories import TaskRepository
from tasks.schemas import TaskCreate, TaskUpdate
from tasks.services import TaskService
from teams.exceptions import TeamNotFoundError
from teams.repositories import TeamMemberRepository, TeamRepository

pytestmark = pytest.mark.asyncio


def _mock_repo(cls):
    return create_autospec(cls, instance=True, spec_set=True)


@pytest.fixture
def task_repo():
    return _mock_repo(TaskRepository)


@pytest.fixture
def team_repo():
    return _mock_repo(TeamRepository)


@pytest.fixture
def team_member_repo():
    return _mock_repo(TeamMemberRepository)


@pytest.fixture
def service(task_repo, team_repo, team_member_repo):
    return TaskService(
        task_repo=task_repo,
        team_repo=team_repo,
        team_member_repo=team_member_repo,
    )


@pytest.fixture
def user():
    """Менеджер команды (id=1)."""
    return SimpleNamespace(id=1)


@pytest.fixture
def member():
    """Обычный участник команды / исполнитель задачи (id=2)."""
    return SimpleNamespace(id=2)


@pytest.fixture
def stranger():
    return SimpleNamespace(id=3)


@pytest.fixture
def team():
    return SimpleNamespace(id=10, manager_id=1)


@pytest.fixture
def task(team, member):
    return SimpleNamespace(
        id=100,
        team_id=team.id,
        team=team,
        assignee_id=member.id,
        status=TaskStatus.OPEN,
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
    )


# --- get_task ---------------------------------------------------------------


async def test_get_task(service, task_repo, user, task):
    task_repo.get_task_by_id.return_value = task

    result = await service.get_task(task.id, user)

    assert result is task
    task_repo.get_task_by_id.assert_awaited_once_with(task.id, user.id)


async def test_get_task_not_found(service, task_repo, user):
    task_repo.get_task_by_id.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.get_task(100, user)

    task_repo.get_task_by_id.assert_awaited_once_with(100, user.id)


# --- get_team_tasks ---------------------------------------------------------


async def test_get_team_tasks(service, task_repo, team_repo, user, task):
    tasks = [task]
    team_repo.get_team_for_user.return_value = task.team
    task_repo.get_tasks_by_team_id.return_value = tasks

    result = await service.get_team_tasks(10, user)

    assert result == tasks
    team_repo.get_team_for_user.assert_awaited_once_with(10, user.id)
    task_repo.get_tasks_by_team_id.assert_awaited_once_with(10, user.id)


# --- get_user_tasks ---------------------------------------------------------


async def test_get_user_tasks(service, task_repo, user, task):
    tasks = [task]
    task_repo.get_tasks_by_user_id.return_value = tasks

    result = await service.get_user_tasks(user)

    assert result == tasks
    task_repo.get_tasks_by_user_id.assert_awaited_once_with(user.id)


# --- get_mean_task_score ----------------------------------------------------


async def test_get_mean_task_score(service, task_repo, user):
    task_repo.get_mean_task_score_for_user.return_value = 4.5

    result = await service.get_mean_task_score(user)

    assert result == {"mean_score": 4.5}
    task_repo.get_mean_task_score_for_user.assert_awaited_once_with(user.id)


async def test_get_mean_task_score_without_scores(service, task_repo, user):
    task_repo.get_mean_task_score_for_user.return_value = None

    result = await service.get_mean_task_score(user)

    assert result == {"mean_score": None}


# --- create_task ------------------------------------------------------------


async def test_create_task(
    service, task_repo, team_repo, team_member_repo, user, team, task,
    create_task_data,
):
    created = SimpleNamespace(id=task.id)
    team_repo.get_team_for_user.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = True
    task_repo.create_task.return_value = created
    task_repo.get_task_by_id.return_value = task

    result = await service.create_task(create_task_data, user)

    assert result is task
    team_repo.get_team_for_user.assert_awaited_once_with(
        create_task_data.team_id, user.id
    )
    team_member_repo.check_member_exists_with_user_id_and_team_id.assert_awaited_once_with(
        create_task_data.assignee_id, create_task_data.team_id
    )
    task_repo.create_task.assert_awaited_once_with(data=create_task_data)
    task_repo.get_task_by_id.assert_awaited_once_with(created.id, user.id)


async def test_create_task_team_not_found(
    service, task_repo, team_repo, team_member_repo, user, create_task_data
):
    team_repo.get_team_for_user.return_value = None

    with pytest.raises(TeamNotFoundError):
        await service.create_task(create_task_data, user)

    team_member_repo.check_member_exists_with_user_id_and_team_id.assert_not_awaited()
    task_repo.create_task.assert_not_awaited()


async def test_create_task_by_non_manager(
    service, task_repo, team_repo, team_member_repo, user, create_task_data
):
    team_repo.get_team_for_user.return_value = SimpleNamespace(
        id=create_task_data.team_id,
        manager_id=999,
    )

    with pytest.raises(PermissionDeniedError):
        await service.create_task(create_task_data, user)

    team_member_repo.check_member_exists_with_user_id_and_team_id.assert_not_awaited()
    task_repo.create_task.assert_not_awaited()


async def test_create_task_assignee_not_in_team(
    service, task_repo, team_repo, team_member_repo, user, team, create_task_data
):
    team_repo.get_team_for_user.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False

    with pytest.raises(AssigneeNotInTeamError):
        await service.create_task(create_task_data, user)

    task_repo.create_task.assert_not_awaited()


async def test_create_task_without_assignee(
    service, task_repo, team_repo, team_member_repo, user, team, task
):
    data = TaskCreate(
        title="Task without assignee",
        description="Description",
        due_date=date(2030, 1, 10),
        assignee_id=None,
        team_id=team.id,
    )
    team_repo.get_team_for_user.return_value = team
    task_repo.create_task.return_value = SimpleNamespace(id=task.id)
    task_repo.get_task_by_id.return_value = task

    result = await service.create_task(data, user)

    assert result is task
    team_member_repo.check_member_exists_with_user_id_and_team_id.assert_not_awaited()


async def test_create_task_not_found_after_creation(
    service, task_repo, team_repo, team_member_repo, user, team, task,
    create_task_data,
):
    team_repo.get_team_for_user.return_value = team
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = True
    task_repo.create_task.return_value = SimpleNamespace(id=task.id)
    task_repo.get_task_by_id.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.create_task(create_task_data, user)


# --- update_task ------------------------------------------------------------


async def test_update_task_by_manager(
    service, task_repo, user, task, update_task_data
):
    refreshed = SimpleNamespace(id=task.id)
    task_repo.get_task_by_id.side_effect = [task, refreshed]
    task_repo.update_task.return_value = SimpleNamespace(id=task.id)

    result = await service.update_task(update_task_data, user)

    assert result is refreshed
    payload = update_task_data.model_dump(
        exclude_unset=True, exclude={"id", "team_id"}
    )
    task_repo.update_task.assert_awaited_once_with(
        {"id": update_task_data.id, **payload}
    )
    assert task_repo.get_task_by_id.await_count == 2


async def test_update_task_by_member_is_forbidden(
    service, task_repo, member, task, update_task_data
):
    task_repo.get_task_by_id.return_value = task

    with pytest.raises(PermissionDeniedError):
        await service.update_task(update_task_data, member)

    task_repo.update_task.assert_not_awaited()


async def test_update_task_by_assignee_is_forbidden(
    service, task_repo, member, task, update_task_data
):
    task_tmp = SimpleNamespace(
        id=task.id, team_id=task.team_id, team=SimpleNamespace(manager_id=1),
        assignee_id=member.id,
    )
    task_repo.get_task_by_id.return_value = task_tmp

    with pytest.raises(PermissionDeniedError):
        await service.update_task(update_task_data, member)

    task_repo.update_task.assert_not_awaited()


async def test_update_task_not_found(
    service, task_repo, user, update_task_data
):
    task_repo.get_task_by_id.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.update_task(update_task_data, user)

    task_repo.update_task.assert_not_awaited()


async def test_update_task_update_failed(
    service, task_repo, user, task, update_task_data
):
    task_repo.get_task_by_id.return_value = task
    task_repo.update_task.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.update_task(update_task_data, user)

    assert task_repo.get_task_by_id.await_count == 1


async def test_update_task_result_not_found(
    service, task_repo, user, task, update_task_data
):
    task_repo.get_task_by_id.side_effect = [task, None]
    task_repo.update_task.return_value = SimpleNamespace(id=task.id)

    with pytest.raises(TaskNotFoundError):
        await service.update_task(update_task_data, user)

    assert task_repo.get_task_by_id.await_count == 2


async def test_update_task_ignores_team_id_in_payload(
    service, task_repo, user, task, update_task_data
):
    data = update_task_data.model_copy(update={"team_id": 999})
    task_repo.get_task_by_id.side_effect = [task, task]
    task_repo.update_task.return_value = SimpleNamespace(id=task.id)

    await service.update_task(data, user)

    called_payload = task_repo.update_task.await_args.args[0]
    assert "team_id" not in called_payload
    assert called_payload["id"] == task.id


async def test_update_task_validates_assignee_membership(
    service, task_repo, team_member_repo, user, task, update_task_data
):
    team_member_repo.check_member_exists_with_user_id_and_team_id.return_value = False
    task_repo.get_task_by_id.return_value = task
    task_repo.update_task.return_value = SimpleNamespace(id=task.id)

    with pytest.raises(AssigneeNotInTeamError):
        await service.update_task(update_task_data, user)

    team_member_repo.check_member_exists_with_user_id_and_team_id.assert_awaited_once_with(
        update_task_data.assignee_id, task.team_id
    )


async def test_update_task_to_done_can_set_manager_comment(
    service, task_repo, user, task
):
    data = TaskUpdate(
        id=task.id,
        title="Done task",
        description=None,
        due_date=date(2030, 1, 10),
        status=TaskStatus.DONE,
        score=5,
        assignee_id=2,
        manager_comment="All good",
    )
    task.status = TaskStatus.REVIEW
    task_repo.get_task_by_id.side_effect = [task, task]
    task_repo.update_task.return_value = SimpleNamespace(id=task.id)

    await service.update_task(data, user)

    called_payload = task_repo.update_task.await_args.args[0]
    assert called_payload["manager_comment"] == "All good"


# --- delete_task ------------------------------------------------------------


async def test_delete_task_not_found(service, task_repo, user):
    task_repo.get_task_by_id.return_value = None

    with pytest.raises(TaskNotFoundError):
        await service.delete_task(100, user)

    task_repo.delete_task.assert_not_awaited()


async def test_delete_task_by_stranger(service, task_repo, stranger, task):
    task_repo.get_task_by_id.return_value = task

    with pytest.raises(PermissionDeniedError):
        await service.delete_task(task.id, stranger)

    task_repo.delete_task.assert_not_awaited()


@pytest.mark.parametrize("role", ["assignee", "manager"])
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
async def test_delete_task_awaits_repository(
    service, task_repo, user, member, task, role
):
    actor = member if role == "assignee" else user
    task_repo.get_task_by_id.return_value = task
    task_repo.delete_task.return_value = True

    await service.delete_task(task.id, actor)

    task_repo.delete_task.assert_awaited_once_with(task.id)


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
async def test_delete_task_raises_if_repository_deleted_nothing(
    service, task_repo, user, task
):
    task_repo.get_task_by_id.return_value = task
    task_repo.delete_task.return_value = False

    with pytest.raises(TaskNotFoundError):
        await service.delete_task(task.id, user)
