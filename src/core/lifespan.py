import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config import settings
from redis.asyncio import Redis

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
    )
    try:
        yield
    finally:
        await app.state.redis.aclose()