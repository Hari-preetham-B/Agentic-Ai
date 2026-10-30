"""SQLAlchemy models for adaptive interview intelligence.

These models store interview sessions, questions, question-skill mappings,
interview turns, evaluations, and skill performance results.

Types are dialect-agnostic so tests can run against SQLite in-memory.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    DateTime,
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


class InterviewSession(Base):
    """An interview session for a profile targeting a career."""

    __tablename__ = "interview_sessions"

    id: Mapped[uuid_pk]
    profile_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    career_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("careers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CREATED", server_default="CREATED"
    )
    mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="MIXED", server_default="MIXED"
    )
    difficulty: Mapped[str] = mapped_column(
        String(10), nullable=False, default="MEDIUM", server_default="MEDIUM"
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    current_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("interview_questions.id", ondelete="SET NULL"), nullable=True
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )
    created_at: Mapped[created_at]
    updated_at: Mapped[updated_at]

    turns: Mapped[List["InterviewTurn"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
    skill_results: Mapped[List["InterviewSkillResult"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class InterviewQuestion(Base):
    """A question in the interview question bank."""

    __tablename__ = "interview_questions"

    id: Mapped[uuid_pk]
    career_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("careers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(30), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    source: Mapped[str] = mapped_column(
        String(30), nullable=False, default="CURATED"
    )
    expected_competency: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )
    created_at: Mapped[created_at]

    skill_mappings: Mapped[List["InterviewQuestionSkill"]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )
    turns: Mapped[List["InterviewTurn"]] = relationship(back_populates="question")


class InterviewQuestionSkill(Base):
    """Maps a question to a skill with a relevance score."""

    __tablename__ = "interview_question_skills"

    id: Mapped[uuid_pk]
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("skills.id", ondelete="SET NULL"), nullable=True, index=True
    )
    skill_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[created_at]

    question: Mapped["InterviewQuestion"] = relationship(back_populates="skill_mappings")


class InterviewTurn(Base):
    """An actual question/answer interaction in an interview session."""

    __tablename__ = "interview_turns"

    id: Mapped[uuid_pk]
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interview_questions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    evaluation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )
    created_at: Mapped[created_at]

    session: Mapped["InterviewSession"] = relationship(back_populates="turns")
    question: Mapped["InterviewQuestion"] = relationship(back_populates="turns")
    evaluation: Mapped[Optional["InterviewEvaluation"]] = relationship(
        back_populates="turn", uselist=False, cascade="all, delete-orphan"
    )


class InterviewEvaluation(Base):
    """Structured evaluation output for an interview turn."""

    __tablename__ = "interview_evaluations"

    id: Mapped[uuid_pk]
    turn_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interview_turns.id", ondelete="CASCADE"),
        nullable=False, unique=True, index=True,
    )
    overall_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    correctness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    depth_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    clarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reasoning_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    strengths: Mapped[Optional[list[str]]] = mapped_column(sa_json(), nullable=True)
    weaknesses: Mapped[Optional[list[str]]] = mapped_column(sa_json(), nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[created_at]

    turn: Mapped["InterviewTurn"] = relationship(back_populates="evaluation")


class InterviewSkillResult(Base):
    """Aggregated session-level performance by skill."""

    __tablename__ = "interview_skill_results"

    id: Mapped[uuid_pk]
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    skill_name: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    questions_attempted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    average_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    latest_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend: Mapped[str] = mapped_column(String(20), nullable=False, default="INSUFFICIENT_DATA")
    performance_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence_metadata: Mapped[Optional[dict]] = mapped_column(sa_json(), nullable=True)
    updated_at: Mapped[updated_at]

    __table_args__ = (
        UniqueConstraint("session_id", "skill_name", name="uq_session_skill"),
    )

    session: Mapped["InterviewSession"] = relationship(back_populates="skill_results")


__all__ = [
    "InterviewSession",
    "InterviewQuestion",
    "InterviewQuestionSkill",
    "InterviewTurn",
    "InterviewEvaluation",
    "InterviewSkillResult",
]
