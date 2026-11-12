import pytest

from tasks.models import Task
from tasks.repositories import TaskRepository
from tasks.schemas import TaskCreate

pytestmark = pytest.mark.asyncio

MISSING_ID = 999_999

# Кто имеет доступ к задаче scene.task: исполнитель, участник команды, менеджер.
ACCESS_ROLES = ["assignee", "member", "manager"]


@pytest.fixture
def repository(uow):
    return TaskRepository(uow)


# --- create_task ------------------------------------------------------------

async def test_create_task(repository, make_user, make_team, day):
    assignee = await make_user()
    team = await make_team()
    # status не указан: берётся значение по умолчанию из схемы.
    # Если у TaskCreate он обязателен, добавь его сюда.
    data = TaskCreate(
        title="Write tests",
        description="Cover repositories",
        due_date=day(2),
        assignee_id=assignee.id,
        team_id=team.id,
    )

    task = await repository.create_task(data)

    assert isinstance(task, Task)
    assert task.id is not None
    assert task.title == "Write tests"
    assert task.description == "Cover repositories"
    assert task.due_date == day(2)
    assert task.status == data.status
    assert task.assignee_id == assignee.id
    assert task.team_id == team.id


# --- get_task_by_id ---------------------------------------------------------

@pytest.mark.parametrize("role", ACCESS_ROLES)
async def test_get_task_by_id_with_access(repository, scene, detach, role):
    task_id = scene.task.id
    user_id = getattr(scene, role).id
    await detach()

    found = await repository.get_task_by_id(task_id, user_id)

    assert found is not None
    assert found.id == task_id


async def test_get_task_by_id_without_access(repository, scene):
    assert await repository.get_task_by_id(scene.task.id, scene.stranger.id) is None


async def test_get_task_by_id_not_found(repository, scene):
    assert await repository.get_task_by_id(MISSING_ID, scene.assignee.id) is None


async def test_get_task_by_id_loads_relations(repository, scene, make_comment, detach):
    comment_1 = await make_comment(scene.task, scene.member)
    comment_2 = await make_comment(scene.task, scene.assignee)
    task_id, team_id, assignee_id = scene.task.id, scene.team.id, scene.assignee.id
    comment_ids = {comment_1.id, comment_2.id}
    await detach()

    found = await repository.get_task_by_id(task_id, assignee_id)

    assert found is not None
    # связи подгружены (иначе MissingGreenlet)
    assert found.team.id == team_id
    assert found.assignee.id == assignee_id
    assert {c.id for c in found.comments} == comment_ids


# --- is_task_exists_for_user ------------------------------------------------

@pytest.mark.parametrize("role", ACCESS_ROLES)
async def test_is_task_exists_for_user_with_access(repository, scene, role):
    user = getattr(scene, role)

    assert await repository.is_task_exists_for_user(scene.task.id, user.id) is True


async def test_is_task_exists_for_user_without_access(repository, scene):
    result = await repository.is_task_exists_for_user(scene.task.id, scene.stranger.id)

    assert result is False


async def test_is_task_exists_for_user_task_not_found(repository, scene):
    result = await repository.is_task_exists_for_user(MISSING_ID, scene.assignee.id)

    assert result is False


# --- get_tasks_by_team_id ---------------------------------------------------

async def test_get_tasks_by_team_id_orders_by_due_date_nulls_last(
    repository, scene, make_task, detach
):
    # scene.task создана первой и без срока
    late = await make_task(scene.team, assignee=scene.assignee, due_d=5)
    early_1 = await make_task(scene.team, assignee=scene.assignee, due_d=1)
    early_2 = await make_task(scene.team, assignee=scene.assignee, due_d=1)
    # сначала по сроку, при равных сроках по id, задачи без срока в конце
    expected = [early_1.id, early_2.id, late.id, scene.task.id]
    team_id, user_id = scene.team.id, scene.member.id
    await detach()

    tasks = await repository.get_tasks_by_team_id(team_id, user_id)

    assert [t.id for t in tasks] == expected
    # assignee подгружен
    assert all(t.assignee.id == scene.assignee.id for t in tasks)


async def test_get_tasks_by_team_id_excludes_other_teams(
    repository, scene, make_team, make_task
):
    other_team = await make_team()
    await make_task(other_team, assignee=scene.assignee)

    tasks = await repository.get_tasks_by_team_id(scene.team.id, scene.member.id)

    assert [t.id for t in tasks] == [scene.task.id]


async def test_get_tasks_by_team_id_manager_sees_all(repository, scene, make_task):
    other = await make_task(scene.team, assignee=scene.member)

    tasks = await repository.get_tasks_by_team_id(scene.team.id, scene.manager.id)

    assert {t.id for t in tasks} == {scene.task.id, other.id}


async def test_get_tasks_by_team_id_assignee_sees_only_own_tasks(
    repository, scene, make_task
):
    # assignee не участник команды, поэтому видит только свои задачи
    await make_task(scene.team, assignee=scene.member)

    tasks = await repository.get_tasks_by_team_id(scene.team.id, scene.assignee.id)

    assert [t.id for t in tasks] == [scene.task.id]


async def test_get_tasks_by_team_id_stranger_sees_nothing(repository, scene):
    tasks = await repository.get_tasks_by_team_id(scene.team.id, scene.stranger.id)

    assert tasks == []


# --- get_tasks_by_user_id ---------------------------------------------------

async def test_get_tasks_by_user_id(repository, scene, make_team, make_task, detach):
    other_team = await make_team()
    late = await make_task(other_team, assignee=scene.assignee, due_d=5)
    early = await make_task(scene.team, assignee=scene.assignee, due_d=1)
    await make_task(scene.team, assignee=scene.member, due_d=2)  # чужая задача
    # по сроку, задача без срока (scene.task) в конце
    expected = [early.id, late.id, scene.task.id]
    user_id = scene.assignee.id
    await detach()

    tasks = await repository.get_tasks_by_user_id(user_id)

    assert [t.id for t in tasks] == expected
    # team подгружена
    assert all(t.team.id == t.team_id for t in tasks)


async def test_get_tasks_by_user_id_empty(repository, scene):
    assert await repository.get_tasks_by_user_id(scene.stranger.id) == []


# --- get_mean_task_score_for_user -------------------------------------------

async def test_get_mean_task_score_for_user(repository, scene, make_task):
    await make_task(scene.team, assignee=scene.assignee, score=4)
    await make_task(scene.team, assignee=scene.assignee, score=5)
    await make_task(scene.team, assignee=scene.assignee, score=None)  # не учитывается
    await make_task(scene.team, assignee=scene.member, score=1)  # чужая

    result = await repository.get_mean_task_score_for_user(scene.assignee.id)

    assert result == pytest.approx(4.5)


async def test_get_mean_task_score_for_user_without_scores(repository, scene):
    # у scene.task оценки нет
    assert await repository.get_mean_task_score_for_user(scene.assignee.id) is None


async def test_get_mean_task_score_for_user_without_tasks(repository, scene):
    assert await repository.get_mean_task_score_for_user(scene.stranger.id) is None


# --- get_user_tasks_in_time -------------------------------------------------
# Окно запроса: дни 1 - 3 от 2030-01-01, границы включительно.

async def test_get_user_tasks_in_time(repository, scene, make_task, day, detach):
    at_start = await make_task(scene.team, assignee=scene.assignee, due_d=1)
    inside = await make_task(scene.team, assignee=scene.assignee, due_d=2)
    at_end = await make_task(scene.team, assignee=scene.assignee, due_d=3)
    await make_task(scene.team, assignee=scene.assignee, due_d=0)  # раньше окна
    await make_task(scene.team, assignee=scene.assignee, due_d=4)  # позже окна
    await make_task(scene.team, assignee=scene.member, due_d=2)  # чужая
    # scene.task без срока в окно не попадает
    expected = {at_start.id, inside.id, at_end.id}
    user_id = scene.assignee.id
    await detach()

    tasks = await repository.get_user_tasks_in_time(
        day(1),
        day(3),
        user_id,
    )

    assert {t.id for t in tasks} == expected
    # team подгружена
    assert all(t.team.id == t.team_id for t in tasks)


async def test_get_user_tasks_in_time_empty(repository, scene, day_dt):
    assert await repository.get_user_tasks_in_time(day_dt(1), day_dt(3), scene.assignee.id) == []


# --- update_task ------------------------------------------------------------

async def test_update_task(repository, scene):
    updated = await repository.update_task(
        {"id": scene.task.id, "title": "Renamed", "description": "New description"}
    )

    assert updated is not None
    assert updated.id == scene.task.id
    assert updated.title == "Renamed"
    assert updated.description == "New description"


async def test_update_task_changes_only_given_fields(repository, scene):
    original_assignee_id = scene.task.assignee_id
    original_team_id = scene.task.team_id

    updated = await repository.update_task({"id": scene.task.id, "title": "Renamed"})

    assert updated is not None
    assert updated.title == "Renamed"
    assert updated.assignee_id == original_assignee_id
    assert updated.team_id == original_team_id


async def test_update_task_not_found(repository):
    result = await repository.update_task({"id": MISSING_ID, "title": "Renamed"})

    assert result is None