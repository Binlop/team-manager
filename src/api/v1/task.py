from fastapi import APIRouter, status
from tasks.schemas import TaskCreate, TaskUpdate, TaskRead, TaskReadBrief, UserTasks, CommentRead, CommentReadBrief, CommentCreate, CommentUpdate
from tasks.deps import TaskServiceDep, CommentServiceDep
from api.deps import UserDep

task_router = APIRouter(prefix="/tasks", tags=["Tasks"])
comment_router = APIRouter(prefix="/comments", tags=["Comments"])

@task_router.get('/my-tasks', response_model=list[UserTasks], status_code=status.HTTP_200_OK)
async def get_user_tasks(service: TaskServiceDep, user: UserDep):
    return await service.get_user_tasks(user)

@task_router.get('/mean-score', status_code=status.HTTP_200_OK)
async def get_mean_task_score(service: TaskServiceDep, user: UserDep):
    return await service.get_mean_task_score(user)

@task_router.post('/', response_model=TaskRead, status_code=status.HTTP_201_CREATED)
async def create_task(data: TaskCreate, service: TaskServiceDep, user: UserDep):
    return await service.create_task(data, user)

@task_router.get('/{task_id}', response_model=TaskRead, status_code=status.HTTP_200_OK)
async def get_task(task_id: int, service: TaskServiceDep, user: UserDep):
    return await service.get_task(task_id, user)

@task_router.put('/{task_id}', response_model=TaskRead, status_code=status.HTTP_200_OK)
async def update_task(task_id: int, data: TaskUpdate, service: TaskServiceDep, user: UserDep):
    return await service.update_task(data, user)

@task_router.get('/team-tasks/{team_id}', response_model=list[TaskReadBrief], status_code=status.HTTP_200_OK)
async def get_team_tasks(team_id: int, service: TaskServiceDep, user: UserDep):
    return await service.get_team_tasks(team_id, user)

@task_router.get('/{task_id}/comments', response_model=list[CommentRead], status_code=status.HTTP_200_OK)
async def get_task_comments(task_id: int, service: CommentServiceDep, user: UserDep):
    return await service.get_comments_by_task_id(task_id, user)


@comment_router.post('/', response_model=CommentRead, status_code=status.HTTP_201_CREATED)
async def create_comment(data: CommentCreate, service: CommentServiceDep, user: UserDep):
    return await service.create_comment(data, user)

@comment_router.get('/{comment_id}', response_model=CommentRead, status_code=status.HTTP_200_OK)
async def get_comment(comment_id: int, service: CommentServiceDep, user: UserDep):
    return await service.get_comment_by_id(comment_id, user)

@comment_router.put('/{comment_id}', response_model=CommentRead, status_code=status.HTTP_200_OK)
async def update_comment(
    comment_id: int, 
    data: CommentUpdate, 
    service: CommentServiceDep, 
    user: UserDep
):
    return await service.update_comment(comment_id, data, user)

@comment_router.delete('/{comment_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int, 
    service: CommentServiceDep, 
    user: UserDep
):
    return await service.delete_comment(comment_id, user)