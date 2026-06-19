from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from typing import AsyncGenerator

from app.config import settings


class Base(DeclarativeBase):
    pass


async_engine = create_async_engine(settings.database_url, echo=False)
sync_engine = create_engine(settings.sync_database_url, echo=False)

AsyncSessionLocal = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)
SyncSessionLocal = sessionmaker(sync_engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with async_engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        from app.models import db_models  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
