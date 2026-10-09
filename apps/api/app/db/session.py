from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import get_settings
from app.models.base import Base

settings = get_settings()

engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}

if settings.database_url.startswith("mysql"):
    engine_kwargs["pool_recycle"] = 3600

engine = create_async_engine(settings.database_url, **engine_kwargs)
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    # Automatically create tables if they do not exist
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
