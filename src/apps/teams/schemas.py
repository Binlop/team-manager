from pydantic import BaseModel, Field
from teams.models import TeamRole
from auth.schemas import UserRead

class TeamBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    invite_code: str = Field(..., min_length=6, max_length=6)

class TeamCreate(TeamBase):
    manager_id: int

class TeamRead(TeamBase):
    manager: UserRead

class TeamMemberRead(BaseModel):
    user: UserRead
    team: TeamBase
    role: TeamRole 

class TeamMemberCreate(BaseModel):
    user_id: int
    team_id: int
    role: TeamRole 

class TeamMemberUpdate(BaseModel):
    id: int
    team_id: int
    role: TeamRole