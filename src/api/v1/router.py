from fastapi import APIRouter
from api.v1.auth import router as auth_router
from api.v1.team import router as team_router

router = APIRouter(prefix="/api/v1")
router.include_router(auth_router)
router.include_router(team_router)