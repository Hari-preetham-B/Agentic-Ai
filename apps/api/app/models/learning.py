"""SQLAlchemy models for learning intelligence and career roadmaps.

These models store learning resources, skill dependencies, roadmaps, and
roadmap items. They are persistence models only; Pydantic schemas serve as
the public API contract.

Types are dialect-agnostic so tests can run against SQLite in-memory.
"""

from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import (
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at, updated_at, uuid_pk


def sa_json():
    """Return a JSON column type portable across SQLite and PostgreSQL."""
    from sqlalchemy import JSON

    return JSON()


class LearningResource(Base):
    """A curated learning resource (course, tutorial, documentation, etc.)."""

    __tablename__ = "learning_resources"

    id: Mapped[uuid_pk]
    title: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )
    created_at: Mapped[created_at]

    skill_mappings: Mapped[List["LearningResourceSkill"]] = relationship(
        back_populates="resource", cascade="all, delete-orphan"
    )


class SkillDependency(Base):
    """A prerequisite relationship between two skills."""

    __tablename__ = "skill_dependencies"

    id: Mapped[uuid_pk]
    skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    prerequisite_skill_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False, index=True
    )
    strength: Mapped[str] = mapped_column(String(20), nullable=False, default="REQUIRED")
    source_reference: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[created_at]

    __table_args__ = (
        UniqueConstraint(
            "skill_id", "prerequisite_skill_id",
            name="uq_skill_dependency",
        ),
    )


class LearningResourceSkill(Base):
    """Many-to-many mapping between learning resources and skills."""

    __tablename__ = "learning_resource_skills"

    id: Mapped[uuid_pk]
    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learning_resources.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    skill_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    coverage_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[created_at]

    resource: Mapped["LearningResource"] = relationship(back_populates="skill_mappings")


class Roadmap(Base):
    """A personalized learning roadmap for a profile targeting a career."""

    __tablename__ = "roadmaps"

    id: Mapped[uuid_pk]
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    career_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("careers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="GENERATED")
    generated_at: Mapped[created_at]
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )

    items: Mapped[List["RoadmapItem"]] = relationship(
        back_populates="roadmap", cascade="all, delete-orphan"
    )


class RoadmapItem(Base):
    """A single skill in a learning roadmap."""

    __tablename__ = "roadmap_items"

    id: Mapped[uuid_pk]
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True
    )
    skill_name: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(5), nullable=False, default="P2")
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_proficiency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    target_proficiency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    prerequisites: Mapped[Optional[list[str]]] = mapped_column(sa_json(), nullable=True)
    created_at: Mapped[created_at]

    roadmap: Mapped["Roadmap"] = relationship(back_populates="items")
    resources: Mapped[List["RoadmapResource"]] = relationship(
        back_populates="roadmap_item", cascade="all, delete-orphan"
    )


class RoadmapResource(Base):
    """Mapping between a roadmap item and a learning resource."""

    __tablename__ = "roadmap_resources"

    id: Mapped[uuid_pk]
    roadmap_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("roadmap_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    resource_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("learning_resources.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[created_at]

    roadmap_item: Mapped["RoadmapItem"] = relationship(back_populates="resources")
    resource: Mapped["LearningResource"] = relationship()


__all__ = [
    "LearningResource",
    "SkillDependency",
    "LearningResourceSkill",
    "Roadmap",
    "RoadmapItem",
    "RoadmapResource",
]
