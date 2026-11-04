from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from db.session import AsyncSession as LocalSession

class UnitOfWork:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def commit(self) -> None:
        await self.db.commit()

    async def rollback(self) -> None:
        await self.db.rollback()

    async def __aenter__(self) -> 'UnitOfWork':
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()

async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    async with LocalSession() as session:
        async with UnitOfWork(session) as uow:
            yield uow