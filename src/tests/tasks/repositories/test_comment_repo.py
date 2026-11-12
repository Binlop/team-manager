import pytest
from sqlalchemy import func, select

from tasks.models import Comment
from tasks.repositories import CommentRepository
from tasks.schemas import CommentCreate, CommentUpdate

pytestmark = pytest.mark.asyncio

MISSING_ID = 999_999

# Кто имеет доступ к задаче scene.task: исполнитель, участник команды, менеджер.
ACCESS_ROLES = ["assignee", "member", "manager"]


@pytest.fixture
def repository(uow):
    return CommentRepository(uow)


async def comment_exists(session, comment_id: int) -> bool:
    count = await session.scalar(
        select(func.count()).select_from(Comment).where(Comment.id == comment_id)
    )
    return count == 1


# --- create_comment ---------------------------------------------------------

async def test_create_comment(repository, scene):
    data = CommentCreate(description="LGTM", task_id=scene.task.id)

    comment = await repository.create_comment(data, scene.member.id)

    assert isinstance(comment, Comment)
    assert comment.id is not None
    assert comment.description == "LGTM"
    assert comment.author_id == scene.member.id
    assert comment.task_id == scene.task.id


# --- get_comment_by_id ------------------------------------------------------

@pytest.mark.parametrize("role", ACCESS_ROLES)
async def test_get_comment_by_id_with_access(repository, scene, make_comment, detach, role):
    comment = await make_comment(scene.task, scene.member)
    comment_id, author_id, task_id = comment.id, scene.member.id, scene.task.id
    user_id = getattr(scene, role).id
    await detach()

    found = await repository.get_comment_by_id(comment_id, user_id)

    assert found is not None
    assert found.id == comment_id
    # author и task подгружены (иначе MissingGreenlet)
    assert found.author.id == author_id
    assert found.task.id == task_id


async def test_get_comment_by_id_without_access(repository, scene, make_comment):
    comment = await make_comment(scene.task, scene.member)

    assert await repository.get_comment_by_id(comment.id, scene.stranger.id) is None


async def test_get_comment_by_id_not_found(repository, scene):
    assert await repository.get_comment_by_id(MISSING_ID, scene.assignee.id) is None


# --- get_comments_by_task_id ------------------------------------------------
# В запросе нет order_by, поэтому порядок в тестах не проверяется.

@pytest.mark.parametrize("role", ACCESS_ROLES)
async def test_get_comments_by_task_id_with_access(
    repository, scene, make_comment, make_task, detach, role
):
    comment_1 = await make_comment(scene.task, scene.member)
    comment_2 = await make_comment(scene.task, scene.assignee)
    other_task = await make_task(scene.team, assignee=scene.assignee)
    await make_comment(other_task, scene.member)  # комментарий к другой задаче
    expected = {comment_1.id, comment_2.id}
    task_id = scene.task.id
    user_id = getattr(scene, role).id
    await detach()

    comments = await repository.get_comments_by_task_id(task_id, user_id)

    assert {c.id for c in comments} == expected
    # author и task подгружены
    assert all(c.author.id == c.author_id for c in comments)
    assert all(c.task.id == task_id for c in comments)


async def test_get_comments_by_task_id_without_access(repository, scene, make_comment):
    await make_comment(scene.task, scene.member)

    comments = await repository.get_comments_by_task_id(scene.task.id, scene.stranger.id)

    assert comments == []


async def test_get_comments_by_task_id_empty(repository, scene):
    comments = await repository.get_comments_by_task_id(scene.task.id, scene.assignee.id)

    assert comments == []


# --- update_comment ---------------------------------------------------------

async def test_update_comment(repository, scene, make_comment):
    comment = await make_comment(scene.task, scene.member, description="Old")

    updated = await repository.update_comment(
        comment.id, CommentUpdate(description="Edited"), scene.member.id
    )

    assert updated is not None
    assert updated.id == comment.id
    assert updated.description == "Edited"
    assert updated.author_id == scene.member.id
    assert updated.task_id == scene.task.id


async def test_update_comment_not_found(repository):
    result = await repository.update_comment(MISSING_ID, CommentUpdate(description="Edited"), 999)

    assert result is None


# --- delete_comment ---------------------------------------------------------

async def test_delete_comment_by_author(repository, session, scene, make_comment):
    comment = await make_comment(scene.task, scene.member)

    deleted = await repository.delete_comment(comment.id, scene.member.id)

    assert deleted is True
    assert await comment_exists(session, comment.id) is False


async def test_delete_comment_by_non_author(repository, session, scene, make_comment):
    comment = await make_comment(scene.task, scene.member)

    # даже менеджер команды не может удалить чужой комментарий
    deleted = await repository.delete_comment(comment.id, scene.manager.id)

    assert deleted is False
    assert await comment_exists(session, comment.id) is True


async def test_delete_comment_not_found(repository, scene):
    assert await repository.delete_comment(MISSING_ID, scene.member.id) is False