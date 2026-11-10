"""Alembic environment configuration.

Connects to PostgreSQL via SQLAlchemy async (asyncpg). Migrations run against
a synchronous connection obtained from the async engine using run_sync, which
is the supported pattern for async SQLAlchemy + Alembic.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

from app.core.config import get_settings
from app.models.base import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support.
target_metadata = Base.metadata

# Override the sqlalchemy.url with the value from settings if available.
# Fall back to a shared in-memory SQLite database so Alembic can be run
# locally without a configured PostgreSQL instance.
settings = get_settings()
if settings.database_url:
    config.set_main_option("sqlalchemy.url", settings.database_url)
else:
    config.set_main_option(
        "sqlalchemy.url", "sqlite+aiosqlite:///:memory:?cache=shared"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an
    Engine is acceptable here as well.  By skipping the Engine creation we
    don't even need a DBAPI to be available.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_online() -> None:
    """Run migrations in 'online' mode using an async engine."""
    url = config.get_main_option("sqlalchemy.url")
    from app.core.database import engine_kwargs

    extra = {k: v for k, v in engine_kwargs(url).items() if k == "connect_args"}
    connectable = create_async_engine(url, poolclass=pool.NullPool, **extra)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_online())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
