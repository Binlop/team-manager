from fastapi import APIRouter
from api.v1.auth import router as auth_router
from api.v1.team import team_router as team_router
from api.v1.team import meeting_router as meeting_router
from api.v1.task import task_router as task_router
from api.v1.task import comment_router as comment_router
from api.v1.agenda import calendar_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(team_router)
router.include_router(meeting_router)
router.include_router(task_router)
router.include_router(comment_router)
router.include_router(calendar_router)