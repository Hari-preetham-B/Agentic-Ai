"""Database session and engine management.

Uses SQLAlchemy 2.x asyncio with asyncpg against PostgreSQL (Supabase).
The engine is created lazily so the application remains importable even when
DATABASE_URL is not configured (e.g. during early development). When no
DATABASE_URL is set, a shared in-memory SQLite database is used so the app
starts and tests can run without a real PostgreSQL instance.
"""

import asyncio
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.models.base import Base, uuid_pk, created_at, updated_at  # noqa: F401


_engine = None
_session_factory = None


def _resolve_database_url() -> str:
    """Resolve the database URL from settings.

    Falls back to a shared in-memory SQLite database when DATABASE_URL is not
    set. The `cache=shared` parameter lets multiple connections see the same
    in-memory database, which is required for tests.
    """
    settings = get_settings()
    if settings.database_url:
        return settings.database_url
    return "sqlite+aiosqlite:///:memory:?cache=shared"


def get_engine():
    """Create (once) and return the async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(_resolve_database_url(), echo=False, pool_pre_ping=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return a cached async sessionmaker bound to the engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    The transaction is committed when the request completes successfully and
    rolled back when it raises, so writes made inside a route are actually
    persisted instead of being discarded when the session closes.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()


async def dispose_engine() -> None:
    """Dispose the engine (useful in tests)."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


async def create_all() -> None:
    """Create all tables on the current engine (used in tests/bootstrap)."""
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def set_engine_for_testing(engine) -> None:
    """Replace the module-level engine/session (testing only)."""
    global _engine, _session_factory
    _engine = engine
    _session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
