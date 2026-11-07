from pydantic import BaseModel, ConfigDict
from tasks.schemas import TaskBase
from teams.schemas import TeamBase, MeetingBase
from auth.schemas import UserRead

class CalendarTaskRead(TaskBase):
    team: TeamBase

class CalendarMeeting(MeetingBase):
    organizer: UserRead

class CalendarRead(BaseModel):
    tasks: list[CalendarTaskRead]
    meetings: list[CalendarMeeting]

    model_config = ConfigDict(from_attributes=True)