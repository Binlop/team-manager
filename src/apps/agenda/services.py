from datetime import datetime
from teams.repositories import MeetingRepository
from tasks.repositories import TaskRepository
from auth.models import User

class AgendaService:

    def __init__(
            self,
            meeting_repo: MeetingRepository,
            task_repo: TaskRepository,
    ) -> None:
        self.meeting_repo = meeting_repo
        self.task_repo = task_repo

    async def get_user_agends(self, starts_at: datetime, ends_at: datetime, user: User):
        meetings = await self.meeting_repo.get_user_meetings_in_time(starts_at, ends_at, user.id)
        tasks = await self.task_repo.get_user_tasks_in_time(starts_at, ends_at, user.id)
        payload = {"meetings": meetings, "tasks": tasks}
        return payload