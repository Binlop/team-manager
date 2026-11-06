from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, model_validator
from teams.models import TeamRole, MeetingStatus
from auth.schemas import UserRead

class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    invite_code: str = Field(..., min_length=6, max_length=6)

    model_config = ConfigDict(from_attributes=True)

class TeamRead(TeamBase):
    manager: UserRead

class TeamReadBrief(TeamBase):
    id: int

class TeamCreate(TeamBase):
    manager_id: int

class TeamMemberRead(BaseModel):
    user: UserRead
    team: TeamBase
    role: TeamRole 

    model_config = ConfigDict(from_attributes=True)

class TeamMemberCreate(BaseModel):
    user_id: int
    team_id: int
    role: TeamRole 

    model_config = ConfigDict(from_attributes=True)

class TeamMemberUpdate(BaseModel):
    id: int
    team_id: int
    role: TeamRole

    model_config = ConfigDict(from_attributes=True)

class MeetingBase(BaseModel):
    name: str = Field(..., max_length=200)
    starts_at: datetime
    ends_at: datetime
    status: MeetingStatus

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def validate_meeting_time(self):
        if self.ends_at < self.starts_at:
            raise ValueError("Время окончания встречи должно быть позже времени начала")
        return self
    
class MeetingRead(MeetingBase):
    id: int

class MeetingCreate(MeetingBase):
    pass

class MeetingUpdate(MeetingBase):
    pass