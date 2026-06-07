from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker,
    AsyncEngine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import get_settings

settings = get_settings()


def create_engine(database_url: str | None = None, echo: bool | None = None) -> AsyncEngine:
    url = database_url or settings.DATABASE_URL
    debug = echo if echo is not None else settings.DEBUG

    connect_args: dict = {}
    extra_kwargs: dict = {}

    if "postgresql" in url:
        connect_args = {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
        }
        extra_kwargs = {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }

    return create_async_engine(
        url,
        echo=debug,
        connect_args=connect_args,
        **extra_kwargs,
    )


engine = create_engine()

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_readonly_db() -> AsyncGenerator[AsyncSession, None]:
    """Read-only session — rolls back instead of committing to avoid accidental writes."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
