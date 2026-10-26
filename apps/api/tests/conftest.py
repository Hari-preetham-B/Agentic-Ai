"""Pytest configuration and async database fixtures for CareerTwin tests.

Tests run against a file-based SQLite database (aiosqlite) so no
real PostgreSQL instance is required. The service functions receive the
session directly, avoiding FastAPI dependency injection in tests.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, set_engine_for_testing


@pytest_asyncio.fixture(scope="session", autouse=True)
async def engine() -> AsyncGenerator:
    """Create a file-based SQLite database with all tables, shared across tests."""
    tmpdir = Path(tempfile.mkdtemp(prefix="careertwin_test_"))
    db_path = tmpdir / "test.db"
    eng = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}", echo=False
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_engine_for_testing(eng)
    yield eng
    await eng.dispose()
    # Clean up temp directory
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest_asyncio.fixture(scope="function")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh async session backed by the shared test database."""
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as sess:
        yield sess
