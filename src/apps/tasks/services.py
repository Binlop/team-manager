from core.exceptions import PermissionDeniedError
from tasks.repositories import TaskRepository, CommentRepository
from tasks.schemas import TaskCreate, TaskUpdate, CommentCreate, CommentUpdate
from tasks.models import Task, Comment
from tasks.exceptions import AssigneeNotInTeamError, TaskNotFoundError, CommentNotFoundError
from auth.models import User
from teams.repositories import TeamRepository, TeamMemberRepository
from teams.exceptions import TeamNotFoundError


class TaskService:

    def __init__(
            self,
            task_repo: TaskRepository,
            team_repo: TeamRepository,
            team_member_repo: TeamMemberRepository,
    ) -> None:
        self.task_repo = task_repo
        self.team_repo = team_repo
        self.team_member_repo = team_member_repo

    async def get_task(self, task_id: int, user: User) -> Task | None:
        task = await self.task_repo.get_task_by_id(task_id, user.id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    async def get_team_tasks(self, team_id: int, user: User) -> list[Task]:
        tasks = await self.task_repo.get_tasks_by_team_id(team_id, user.id)
        return tasks

    async def get_user_tasks(self, user: User) -> list[Task]:
        tasks = await self.task_repo.get_tasks_by_user_id(user.id)
        return tasks

    async def get_mean_task_score(self, user: User) -> dict[str, float | None]:
        mean_score = await self.task_repo.get_mean_task_score_for_user(user.id)
        payload = {"mean_score": mean_score}
        return payload

    async def create_task(self, data: TaskCreate, user: User) -> Task:
        team = await self.team_repo.get_team_by_id(data.team_id)
        if team is None:
            raise TeamNotFoundError(data.team_id)
        if team.manager_id != user.id:
            raise PermissionDeniedError("Задачи может создавать только менеджер команды")
        if data.assignee_id is not None:
            if not await self.team_member_repo.check_member_exists_with_user_id_and_team_id(data.assignee_id, data.team_id):
                raise AssigneeNotInTeamError(data.assignee_id, data.team_id)
            
        created = await self.task_repo.create_task(data=data)
        task = await self.task_repo.get_task_by_id(created.id, user.id)
        if task is None:
            raise TaskNotFoundError(created.id)
        return task

    async def update_task(self, data: TaskUpdate, user: User) -> Task:
        task = await self.task_repo.get_task_by_id(data.id, user.id)
        if task is None:
            raise TaskNotFoundError(data.id)
        is_manager = task.team.manager_id == user.id
        if is_manager:
            payload = data.model_dump(exclude_unset=True, exclude={"id", "team_id"})
        else:
            payload = data.model_dump(include={"status"}, exclude_unset=True)

        updated = await self.task_repo.update_task({"id": data.id, **payload})
        if updated is None:
            raise TaskNotFoundError(data.id)

        result = await self.task_repo.get_task_by_id(data.id, user.id)
        if result is None:
            raise TaskNotFoundError(data.id)
        return result

class CommentService:

    def __init__(
            self,
            comment_repo: CommentRepository,
            task_repo: TaskRepository,
    ) -> None:
        self.comment_repo = comment_repo
        self.task_repo = task_repo

    async def create_comment(self, data: CommentCreate, user: User) -> Comment:
        can_user_make_comment = await self.task_repo.is_task_exists_for_user(data.task_id, user.id)
        if not can_user_make_comment:
            raise PermissionDeniedError()
        created = await self.comment_repo.create_comment(data=data, user_id=user.id)
        comment = await self.comment_repo.get_comment_by_id(created.id, user.id)
        if comment is None:
            raise CommentNotFoundError(created.id)
        return comment

    async def get_comment_by_id(self, comment_id: int, user: User) -> Comment:
        comment = await self.comment_repo.get_comment_by_id(comment_id, user.id)
        if comment is None:
            raise CommentNotFoundError(comment_id)
        return comment
    
    async def get_comments_by_task_id(self, task_id: int, user: User) -> list[Comment]:
        comments = await self.comment_repo.get_comments_by_task_id(task_id, user.id)
        return comments

    async def update_comment(self, comment_id: int, data: CommentUpdate, user: User) -> Comment:
        comment = await self.comment_repo.get_comment_by_id(comment_id, user.id)
        if comment is None:
            raise CommentNotFoundError(comment_id)
        if comment.author_id != user.id:
            raise PermissionDeniedError()
        updated = await self.comment_repo.update_comment(comment_id, data, user.id)
        if updated is None:
            raise CommentNotFoundError(comment_id)

        result = await self.comment_repo.get_comment_by_id(comment_id, user.id)
        if result is None:
            raise CommentNotFoundError(comment_id)
        return result

    async def delete_comment(self, comment_id: int, user: User) -> None:
        deleted = await self.comment_repo.delete_comment(comment_id, user.id)
        if not deleted:
            raise PermissionDeniedError()
        