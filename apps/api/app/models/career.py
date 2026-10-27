"""SQLAlchemy models for curated career knowledge.

These models store the deterministic, curated career requirement database.
They are NEVER the source of LLM-generated content — career requirements
come from curated, sourced data (e.g. O*NET, BLS, official documentation).

Agents and services read from these tables via the repository layer; they
never execute SQL directly.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at, updated_at, uuid_pk


def sa_json():
    """Return a JSON column type portable across SQLite and PostgreSQL."""
    from sqlalchemy import JSON

    return JSON()


class Career(Base):
    """A curated career profile (e.g. Software Engineer, Data Analyst)."""

    __tablename__ = "careers"

    id: Mapped[uuid_pk]
    slug: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    education_expectations: Mapped[Optional[dict]] = mapped_column(
        sa_json(), nullable=True
    )
    experience_expectations: Mapped[Optional[dict]] = mapped_column(
        sa_json(), nullable=True
    )
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    skills: Mapped[List["CareerSkill"]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    tools: Mapped[List["CareerTool"]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    projects: Mapped[List["CareerProject"]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )
    sources: Mapped[List["CareerSource"]] = relationship(
        back_populates="career", cascade="all, delete-orphan"
    )


class CareerSkill(Base):
    """A skill required or useful for a career, with importance and level."""

    __tablename__ = "career_skills"

    id: Mapped[uuid_pk]
    career_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    minimum_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[created_at]

    career: Mapped["Career"] = relationship(back_populates="skills")


class CareerTool(Base):
    """A tool (software, language, platform) used in a career."""

    __tablename__ = "career_tools"

    id: Mapped[uuid_pk]
    career_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    importance: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[created_at]

    career: Mapped["Career"] = relationship(back_populates="tools")


class CareerProject(Base):
    """A typical project that demonstrates competence in a career."""

    __tablename__ = "career_projects"

    id: Mapped[uuid_pk]
    career_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    skills_demonstrated: Mapped[Optional[list[str]]] = mapped_column(
        sa_json(), nullable=True
    )
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[created_at]

    career: Mapped["Career"] = relationship(back_populates="projects")


class CareerSource(Base):
    """A source reference for curated career requirement data."""

    __tablename__ = "career_sources"

    id: Mapped[uuid_pk]
    career_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("careers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    published_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reliability: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[created_at]

    career: Mapped["Career"] = relationship(back_populates="sources")


__all__ = [
    "Career",
    "CareerSkill",
    "CareerTool",
    "CareerProject",
    "CareerSource",
]
