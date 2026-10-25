"""Shared database column conventions and base model mixins.

Types are kept dialect-agnostic (sa.Uuid, sa.JSON) so the same models can run
against PostgreSQL in production and SQLite in-memory in tests. The Alembic
migration uses PostgreSQL-specific types for production.
"""

import uuid
from datetime import datetime
from typing import Annotated

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""


uuid_pk = Annotated[
    uuid.UUID,
    mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    ),
]
created_at = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
]
updated_at = Annotated[
    datetime,
    mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    ),
]
