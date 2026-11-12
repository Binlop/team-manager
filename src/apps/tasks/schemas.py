from datetime import date
from pydantic import BaseModel, Field, ConfigDict
from tasks.models import TaskStatus
from teams.schemas import TeamReadBrief
from auth.schemas import UserRead

class TaskBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str | None = Field(default=None, max_length=500)
    due_date: date
    status: TaskStatus = TaskStatus.OPEN
    score: int | None = None
    model_config = ConfigDict(from_attributes=True)

class TaskReadBrief(TaskBase):
    id: int
    assignee: UserRead

class UserTasks(TaskBase):
    id: int
    team: TeamReadBrief

class TaskRead(TaskReadBrief):
    team: TeamReadBrief
    comments: list[CommentReadBrief]
    score: int | None = None
    manager_comment: str | None

class TaskCreate(TaskBase):
    assignee_id: int | None
    team_id: int

class TaskUpdate(TaskCreate):
    id: int
    score: int | None = None
    manager_comment: str | None

class CommentBase(BaseModel):
    description: str = Field(..., max_length=500)

    model_config = ConfigDict(from_attributes=True)

class CommentRead(CommentBase):
    id: int
    author: UserRead
    task: TaskReadBrief

class CommentReadBrief(CommentBase):
    id: int

class CommentCreate(CommentBase):
    task_id: int

class CommentUpdate(CommentBase):
    pass

