"""SQLAlchemy models for the CareerTwin profile.

These are persistence models only. They are never exposed directly as the
public API contract; Pydantic schemas serve that role.

Types are dialect-agnostic so tests can run against SQLite in-memory. The
Alembic migration uses PostgreSQL-specific types for production.
"""

import uuid
from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at, updated_at, uuid_pk


def sa_json():
    """Return a JSON column type portable across SQLite and PostgreSQL."""
    from sqlalchemy import JSON

    return JSON()


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid_pk]
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True, index=True
    )
    full_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    headline: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="DRAFT", server_default="DRAFT"
    )
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    education: Mapped[List["Education"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    skills: Mapped[List["Skill"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    projects: Mapped[List["Project"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    experience: Mapped[List["Experience"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )
    career_goals: Mapped[List["CareerGoal"]] = relationship(
        back_populates="profile", cascade="all, delete-orphan"
    )


class Education(Base):
    __tablename__ = "education"

    id: Mapped[uuid_pk]
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    institution: Mapped[str] = mapped_column(Text, nullable=False)
    degree: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    field_of_study: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[created_at]

    profile: Mapped["Profile"] = relationship(back_populates="education")


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[uuid_pk]
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proficiency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    years_experience: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 1), nullable=True
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="USER_CONFIRMED", server_default="USER_CONFIRMED"
    )
    created_at: Mapped[created_at]

    profile: Mapped["Profile"] = relationship(back_populates="skills")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid_pk]
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technologies: Mapped[Optional[List[str]]] = mapped_column(
        sa_json(), nullable=True
    )
    role: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    outcomes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="USER_CONFIRMED", server_default="USER_CONFIRMED"
    )
    created_at: Mapped[created_at]

    profile: Mapped["Profile"] = relationship(back_populates="projects")


class Experience(Base):
    __tablename__ = "experience"

    id: Mapped[uuid_pk]
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    organization: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    achievements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="USER_CONFIRMED", server_default="USER_CONFIRMED"
    )
    created_at: Mapped[created_at]

    profile: Mapped["Profile"] = relationship(back_populates="experience")


class CareerGoal(Base):
    __tablename__ = "career_goals"

    id: Mapped[uuid_pk]
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    target_role: Mapped[str] = mapped_column(Text, nullable=False)
    target_industry: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_domain: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    goal_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[created_at]

    profile: Mapped["Profile"] = relationship(back_populates="career_goals")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[uuid_pk]
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True, index=True
    )
    request_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    capability: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    provider: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    events: Mapped[list["AgentEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[uuid_pk]
    agent_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    agent_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(sa_json(), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped["AgentRun"] = relationship(back_populates="events")
