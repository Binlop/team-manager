from fastapi import FastAPI
from api.v1.router import router as v1_router
from core.exception_handlers import register_exception_handlers
from core.config import settings
from core.logging import configure_logging
from core.lifespan import lifespan
from middleware import AccessLogMiddleware
# from fastapi.staticfiles import StaticFiles
configure_logging()

import db.models

app = FastAPI(
    title=settings.PROJECT_NAME, 
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

register_exception_handlers(app)
app.include_router(v1_router)
app.add_middleware(AccessLogMiddleware)
# app.mount("/static", StaticFiles(directory="static"), name="static")