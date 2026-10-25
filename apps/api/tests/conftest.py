"""Pytest configuration and async database fixtures for CareerTwin tests.

Tests run against a shared in-memory SQLite database (aiosqlite) so no
real PostgreSQL instance is required. The service functions receive the
session directly, avoiding FastAPI dependency injection in tests.
"""

import asyncio
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, set_engine_for_testing


@pytest_asyncio.fixture(scope="function")
async def session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async session backed by an in-memory SQLite database."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:?cache=shared", echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    set_engine_for_testing(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as sess:
        yield sess

    await engine.dispose()
