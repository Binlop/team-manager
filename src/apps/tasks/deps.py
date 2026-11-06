from typing import Annotated
from fastapi import Depends
from db.uow import get_uow
from tasks.repositories import TaskRepository, CommentRepository
from teams.deps import TeamRepoDep, TeamMemberRepoDep
from tasks.services import TaskService, CommentService

def get_task_repository(uow=Depends(get_uow)) -> TaskRepository:
    return TaskRepository(uow)

def get_comment_repository(uow=Depends(get_uow)) -> CommentRepository:
    return CommentRepository(uow)

TaskRepoDep = Annotated[TaskRepository, Depends(get_task_repository)]
CommentRepoDep = Annotated[CommentRepository, Depends(get_comment_repository)]

def get_team_service(
    task_repo: TaskRepoDep,
    team_repo: TeamRepoDep,
    team_member_repo: TeamMemberRepoDep,
) -> TaskService:
    return TaskService(task_repo, team_repo, team_member_repo)

def get_comment_service(
    comment_repo: CommentRepoDep,
    task_repo: TaskRepoDep,
) -> CommentService:
    return CommentService(comment_repo, task_repo)

TaskServiceDep = Annotated[TaskService, Depends(get_team_service)]
CommentServiceDep = Annotated[CommentService, Depends(get_comment_service)]
