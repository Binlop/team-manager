from typing import Annotated
from fastapi import Depends
from agenda.services import AgendaService
from teams.deps import MeetingRepoDep
from tasks.deps import TaskRepoDep

def get_agenda_service(
    meeting_repo: MeetingRepoDep,
    task_repo: TaskRepoDep,
) -> AgendaService:
    return AgendaService(meeting_repo, task_repo)

AgendaServiceDep = Annotated[AgendaService, Depends(get_agenda_service)]