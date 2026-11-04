from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import DateTime, func
from core.config import settings
from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

async_engine = create_async_engine(settings.DATABASE_URL)

AsyncSession = async_sessionmaker(autocommit=False, autoflush=False, bind=async_engine, expire_on_commit=False)

class Base(DeclarativeBase):
    created_on: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_on: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

def utcnow():
    return datetime.now(timezone.utc)

async def get_async_db():
    async with AsyncSession() as session:
        yield session