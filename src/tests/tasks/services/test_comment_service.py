# tests/tasks/services/test_comment_service.py

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from core.exceptions import PermissionDeniedError
from tasks.services import CommentService
from tasks.schemas import CommentCreate, CommentUpdate
from tasks.exceptions import CommentNotFoundError


pytestmark = pytest.mark.asyncio


@pytest.fixture
def service():
    comment_repo = AsyncMock()
    task_repo = AsyncMock()

    service = CommentService(
        comment_repo=comment_repo,
        task_repo=task_repo,
    )

    return SimpleNamespace(
        service=service,
        comment_repo=comment_repo,
        task_repo=task_repo,
    )


@pytest.fixture
def user():
    return SimpleNamespace(id=1)


@pytest.fixture
def comment():
    return SimpleNamespace(
        id=100,
        author_id=1,
        task_id=10,
        description="Test comment",
    )


@pytest.fixture
def create_comment_data():
    return CommentCreate(
        task_id=10,
        description="Test comment",
    )


@pytest.fixture
def update_comment_data():
    return CommentUpdate(
        description="Updated comment",
    )


# ---------------------------------------------------------
# create_comment
# ---------------------------------------------------------

async def test_create_comment_success(
    service,
    user,
    comment,
    create_comment_data,
):
    service.task_repo.is_task_exists_for_user.return_value = True
    service.comment_repo.create_comment.return_value = SimpleNamespace(
        id=comment.id,
    )
    service.comment_repo.get_comment_by_id.return_value = comment

    result = await service.service.create_comment(
        create_comment_data,
        user,
    )

    assert result is comment

    service.task_repo.is_task_exists_for_user.assert_awaited_once_with(
        create_comment_data.task_id,
        user.id,
    )

    service.comment_repo.create_comment.assert_awaited_once_with(
        data=create_comment_data,
        user_id=user.id,
    )

    service.comment_repo.get_comment_by_id.assert_awaited_once_with(
        comment.id,
        user.id,
    )


async def test_create_comment_without_task_access(
    service,
    user,
    create_comment_data,
):
    service.task_repo.is_task_exists_for_user.return_value = False

    with pytest.raises(PermissionDeniedError):
        await service.service.create_comment(
            create_comment_data,
            user,
        )

    service.comment_repo.create_comment.assert_not_awaited()
    service.comment_repo.get_comment_by_id.assert_not_awaited()


async def test_create_comment_result_not_found(
    service,
    user,
    comment,
    create_comment_data,
):
    service.task_repo.is_task_exists_for_user.return_value = True
    service.comment_repo.create_comment.return_value = SimpleNamespace(
        id=comment.id,
    )
    service.comment_repo.get_comment_by_id.return_value = None

    with pytest.raises(CommentNotFoundError):
        await service.service.create_comment(
            create_comment_data,
            user,
        )


# ---------------------------------------------------------
# get_comment_by_id
# ---------------------------------------------------------

async def test_get_comment_by_id_success(
    service,
    user,
    comment,
):
    service.comment_repo.get_comment_by_id.return_value = comment

    result = await service.service.get_comment_by_id(
        comment.id,
        user,
    )

    assert result is comment

    service.comment_repo.get_comment_by_id.assert_awaited_once_with(
        comment.id,
        user.id,
    )


async def test_get_comment_by_id_not_found(service, user):
    service.comment_repo.get_comment_by_id.return_value = None

    with pytest.raises(CommentNotFoundError):
        await service.service.get_comment_by_id(100, user)


# ---------------------------------------------------------
# get_comments_by_task_id
# ---------------------------------------------------------

async def test_get_comments_by_task_id(
    service,
    user,
    comment,
):
    comments = [comment]

    service.comment_repo.get_comments_by_task_id.return_value = comments

    result = await service.service.get_comments_by_task_id(
        comment.task_id,
        user,
    )

    assert result == comments

    service.comment_repo.get_comments_by_task_id.assert_awaited_once_with(
        comment.task_id,
        user.id,
    )


async def test_get_comments_by_task_id_empty(service, user):
    service.comment_repo.get_comments_by_task_id.return_value = []

    result = await service.service.get_comments_by_task_id(10, user)

    assert result == []


# ---------------------------------------------------------
# update_comment
# ---------------------------------------------------------

async def test_update_comment_success(
    service,
    user,
    comment,
    update_comment_data,
):
    updated_comment = SimpleNamespace(id=comment.id)

    service.comment_repo.get_comment_by_id.side_effect = [
        comment,
        comment,
    ]
    service.comment_repo.update_comment.return_value = updated_comment

    result = await service.service.update_comment(
        comment.id,
        update_comment_data,
        user,
    )

    assert result is comment

    service.comment_repo.get_comment_by_id.assert_any_await(
        comment.id,
        user.id,
    )

    service.comment_repo.update_comment.assert_awaited_once_with(
        comment.id,
        update_comment_data,
        user.id,
    )

    assert service.comment_repo.get_comment_by_id.await_count == 2


async def test_update_comment_not_found(
    service,
    user,
    update_comment_data,
):
    service.comment_repo.get_comment_by_id.return_value = None

    with pytest.raises(CommentNotFoundError):
        await service.service.update_comment(
            100,
            update_comment_data,
            user,
        )

    service.comment_repo.update_comment.assert_not_awaited()


async def test_update_comment_not_author(
    service,
    user,
    comment,
    update_comment_data,
):
    comment.author_id = 999

    service.comment_repo.get_comment_by_id.return_value = comment

    with pytest.raises(PermissionDeniedError):
        await service.service.update_comment(
            comment.id,
            update_comment_data,
            user,
        )

    service.comment_repo.update_comment.assert_not_awaited()


async def test_update_comment_update_failed(
    service,
    user,
    comment,
    update_comment_data,
):
    service.comment_repo.get_comment_by_id.return_value = comment
    service.comment_repo.update_comment.return_value = None

    with pytest.raises(CommentNotFoundError):
        await service.service.update_comment(
            comment.id,
            update_comment_data,
            user,
        )

    assert service.comment_repo.get_comment_by_id.await_count == 1


async def test_update_comment_result_not_found(
    service,
    user,
    comment,
    update_comment_data,
):
    service.comment_repo.get_comment_by_id.side_effect = [
        comment,
        None,
    ]
    service.comment_repo.update_comment.return_value = SimpleNamespace(
        id=comment.id,
    )

    with pytest.raises(CommentNotFoundError):
        await service.service.update_comment(
            comment.id,
            update_comment_data,
            user,
        )

    assert service.comment_repo.get_comment_by_id.await_count == 2


# ---------------------------------------------------------
# delete_comment
# ---------------------------------------------------------

async def test_delete_comment_success(
    service,
    user,
    comment,
):
    service.comment_repo.delete_comment.return_value = True

    result = await service.service.delete_comment(
        comment.id,
        user,
    )

    assert result is None

    service.comment_repo.delete_comment.assert_awaited_once_with(
        comment.id,
        user.id,
    )


async def test_delete_comment_failed(
    service,
    user,
    comment,
):
    service.comment_repo.delete_comment.return_value = False

    with pytest.raises(PermissionDeniedError):
        await service.service.delete_comment(
            comment.id,
            user,
        )

    service.comment_repo.delete_comment.assert_awaited_once_with(
        comment.id,
        user.id,
    )