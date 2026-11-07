from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Query, status
from agenda.deps import AgendaServiceDep
from agenda.schemas import CalendarRead
from api.deps import UserDep

calendar_router = APIRouter(prefix="/calendar", tags=["Calendar"])

@calendar_router.get('', response_model=CalendarRead, status_code=status.HTTP_200_OK)
async def get_calendar_events(
    service: AgendaServiceDep,
    user: UserDep,
    starts_at: datetime = Query(default_factory=lambda: datetime.now(timezone.utc)), 
    ends_at: datetime = Query(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=1)),  
):
    return await service.get_user_agends(starts_at, ends_at, user)
