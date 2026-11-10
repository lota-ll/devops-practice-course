"""Async SQLAlchemy. Engine створюється ліниво, тож тести можуть підмінити URL."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from .config import get_settings


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(UTC)


_engine: AsyncEngine | None = None
_factory: async_sessionmaker[AsyncSession] | None = None


def configure_db(url: str) -> AsyncEngine:
    """(Пере)налаштувати engine.

    postgresql+psycopg:// — psycopg 3 підтримує і sync (Alembic), і async (застосунок)
    з тим самим URL. Для SQLite у тестах — sqlite+aiosqlite:// без пулу.
    """
    global _engine, _factory
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs = {"poolclass": NullPool}
    _engine = create_async_engine(url, **kwargs)
    _factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def session_factory() -> async_sessionmaker[AsyncSession]:
    if _factory is None:
        configure_db(get_settings().database_url)
    assert _factory is not None
    return _factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: одна сесія на запит."""
    async with session_factory()() as session:
        yield session


async def dispose() -> None:
    if _engine is not None:
        await _engine.dispose()
