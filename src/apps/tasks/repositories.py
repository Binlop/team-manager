from typing import Any
from datetime import date
from sqlalchemy import select, delete, update, exists, or_, func
from sqlalchemy.orm import selectinload, joinedload
from db.uow import UnitOfWork
from teams.models import Team, TeamMember
from tasks.models import Task, Comment
from tasks.schemas import TaskCreate, CommentCreate, CommentUpdate

def _user_has_access_task(user_id: int):
    is_member = (
        exists()
        .where(
            TeamMember.team_id == Task.team_id,
            TeamMember.user_id == user_id,
        )
    )
    is_manager = (
        exists()
        .where(
            Team.id == Task.team_id,
            Team.manager_id == user_id,
        )
    )
    return or_(Task.assignee_id == user_id, is_member, is_manager)

class TaskRepository:

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create_task(self, data: TaskCreate) -> Task:
        task = Task(
            title = data.title,
            description = data.description,
            due_date = data.due_date,
            status = data.status,
            assignee_id = data.assignee_id,
            team_id = data.team_id,
        )
        self.uow.db.add(task)
        await self.uow.db.flush()
        return task

    async def get_task_by_id(self, task_id: int, user_id: int) -> Task | None:
        stmt = (
            select(Task)
            .where(
                Task.id == task_id,
                _user_has_access_task(user_id),
            )
            .options(
                selectinload(Task.comments),
                joinedload(Task.team),
                joinedload(Task.assignee),
            )
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()

    async def is_task_exists_for_user(self, task_id: int, user_id: int) -> bool:
        stmt = (
            select(
                exists().where(
                    Task.id == task_id,
                    _user_has_access_task(user_id),
                ))
        )
        result = await self.uow.db.execute(stmt)
        return result.scalar_one()  

    async def get_tasks_by_team_id(self, team_id: int, user_id: int) -> list[Task]:
        stmt = (
            select(Task)
            .where(
                Task.team_id == team_id,
                 _user_has_access_task(user_id)
            )
            .options(
                joinedload(Task.assignee),
            ).order_by(Task.due_date.asc().nulls_last(), Task.id)
        )
        res = await self.uow.db.execute(stmt)
        return list(res.scalars().all())

    async def get_tasks_by_user_id(self, user_id: int) -> list[Task]:
        stmt = (
            select(Task)
            .where(
                Task.assignee_id == user_id
            )
            .options(
                joinedload(Task.team),
            ).order_by(Task.due_date.asc().nulls_last(), Task.id)
        )
        res = await self.uow.db.execute(stmt)
        return list(res.scalars().all())

    async def get_mean_task_score_for_user(self, user_id: int) -> float | None:
        stmt = (
            select(func.avg(Task.score))
            .where(
                Task.assignee_id == user_id,
                Task.score.is_not(None)
            )
        )
        result = await self.uow.db.scalar(stmt)
        return float(result) if result is not None else None

    async def get_user_tasks_in_time(self, starts_at: date, ends_at: date, user_id: int) -> list[Task]:
        stmt = (
            select(Task).where(
                Task.assignee_id == user_id,
                Task.due_date >= starts_at,
                Task.due_date <= ends_at,
            )
            .options(
                joinedload(Task.team),
            )
            .order_by(Task.due_date, Task.id)
        )
        res = await self.uow.db.execute(stmt)
        return list(res.scalars().all())

    async def update_task(self, data: dict[str, Any]) -> Task | None:
        stmt = (
            update(Task).where(
                Task.id == data['id']
            )
            .values(data).returning(Task)
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()

class CommentRepository:

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create_comment(self, data: CommentCreate, user_id: int) -> Comment:
        comment = Comment(
            description = data.description,
            author_id = user_id,
            task_id = data.task_id,
        )
        self.uow.db.add(comment)
        await self.uow.db.flush()
        return comment

    async def get_comment_by_id(self, comment_id: int, user_id: int) -> Comment | None:
        stmt = (
            select(Comment)
            .join(Comment.task)
            .where(
                Comment.id == comment_id,
                _user_has_access_task(user_id),
            )
            .options(
                joinedload(Comment.author),
                joinedload(Comment.task),
            )
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()
    
    async def get_comments_by_task_id(self, task_id: int, user_id: int) -> list[Comment]:
        stmt = (
            select(Comment)
            .join(Comment.task)
            .where(
                Comment.task_id == task_id,
                _user_has_access_task(user_id),
            )
            .options(
                joinedload(Comment.author),
                joinedload(Comment.task),
            )
            .order_by(Comment.id)
        )
        res = await self.uow.db.execute(stmt)
        return list(res.scalars().all())

    async def update_comment(self, comment_id: int, data: CommentUpdate, user_id: int) -> Comment | None:
        stmt = (
            update(Comment).where(
                Comment.id == comment_id,
                Comment.author_id == user_id
            )
            .values(
                description = data.description,
            )
            .returning(Comment)
        )
        res = await self.uow.db.execute(stmt)
        return res.scalar_one_or_none()

    async def delete_comment(self, comment_id: int, user_id: int) -> bool:
        stmt = (
            delete(Comment).where(
                Comment.id == comment_id,
                Comment.author_id == user_id
            )
        )
        res = await self.uow.db.execute(stmt)
        return res.rowcount > 0 # pyright: ignore[reportAttributeAccessIssue]