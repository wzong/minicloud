from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _ensure_engine() -> None:
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(get_settings().db_url, future=True)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def init_db() -> None:
    _ensure_engine()
    # Importing models registers them on Base.metadata.
    from app import models  # noqa: F401

    assert _engine is not None
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncIterator[AsyncSession]:
    _ensure_engine()
    assert _session_factory is not None
    async with _session_factory() as session:
        yield session
