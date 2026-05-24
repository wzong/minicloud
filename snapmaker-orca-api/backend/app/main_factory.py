"""Small shim so background tasks can grab a fresh session factory without circular imports."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings

_factory: async_sessionmaker[AsyncSession] | None = None


def session_factory() -> async_sessionmaker[AsyncSession]:
    global _factory
    if _factory is None:
        engine = create_async_engine(get_settings().db_url, future=True)
        _factory = async_sessionmaker(engine, expire_on_commit=False)
    return _factory
