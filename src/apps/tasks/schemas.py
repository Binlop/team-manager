from typing_extensions import Self
from datetime import date
from pydantic import BaseModel, Field, ConfigDict, model_validator
from tasks.models import TaskStatus
from teams.schemas import TeamReadBrief
from auth.schemas import UserRead

class TaskBase(BaseModel):
    title: str = Field(..., max_length=200)
    description: str | None = Field(default=None, max_length=500)
    due_date: date
    status: TaskStatus = TaskStatus.OPEN
    score: int | None = Field(default=None, ge=1, le=5)
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
    manager_comment: str | None = Field(default=None, max_length=500)

class TaskCreate(TaskBase):
    assignee_id: int | None
    team_id: int

class TaskUpdate(TaskCreate):
    id: int

    @model_validator(mode="after")
    def validate_done_requires_score(self) -> Self:
        if self.status == TaskStatus.DONE and self.score is None:
            raise ValueError("score is required when status is DONE")
        return self

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

