"""Adaptive interview intelligence schema.

Create the interview intelligence tables:

- interview_sessions
- interview_questions
- interview_question_skills
- interview_turns
- interview_evaluations
- interview_skill_results

Revision ID: 0005_adaptive_interview
Revises: 0004_learning_roadmap
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_adaptive_interview"
down_revision: Union[str, None] = "0004_learning_roadmap"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SESSION_STATUS_CHECK = (
    "status IN ('CREATED', 'ACTIVE', 'PAUSED', 'COMPLETED', 'ABANDONED')"
)
_SESSION_MODE_CHECK = "mode IN ('TECHNICAL', 'BEHAVIORAL', 'MIXED')"
_QUESTION_TYPE_CHECK = (
    "question_type IN ('TECHNICAL', 'CONCEPTUAL', 'SCENARIO', "
    "'BEHAVIORAL', 'SYSTEM_DESIGN', 'PROBLEM_SOLVING')"
)
_DIFFICULTY_CHECK = "difficulty IN ('EASY', 'MEDIUM', 'HARD', 'EXPERT')"
_TURN_EVAL_STATUS_CHECK = (
    "evaluation_status IN ('PENDING', 'EVALUATED', 'FAILED', 'UNAVAILABLE')"
)
_TURN_STATUS_CHECK = "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'SKIPPED')"
_TREND_CHECK = "trend IN ('IMPROVING', 'STABLE', 'DECLINING', 'INSUFFICIENT_DATA')"


def upgrade() -> None:
    op.create_table(
        "interview_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("career_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="CREATED"),
        sa.Column("mode", sa.String(length=20), nullable=False, server_default="MIXED"),
        sa.Column("difficulty", sa.String(length=10), nullable=False, server_default="MEDIUM"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_question_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["profiles.id"], name=op.f("fk_interview_sessions_profile_id_profiles"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["career_id"], ["careers.id"], name=op.f("fk_interview_sessions_career_id_careers"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_sessions")),
        sa.CheckConstraint(_SESSION_STATUS_CHECK, name=op.f("ck_interview_sessions_status")),
        sa.CheckConstraint(_SESSION_MODE_CHECK, name=op.f("ck_interview_sessions_mode")),
    )

    op.create_table(
        "interview_questions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("career_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("question_type", sa.String(length=30), nullable=False),
        sa.Column("difficulty", sa.String(length=10), nullable=False, server_default="MEDIUM"),
        sa.Column("source", sa.String(length=30), nullable=False, server_default="CURATED"),
        sa.Column("expected_competency", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["career_id"], ["careers.id"], name=op.f("fk_interview_questions_career_id_careers"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_questions")),
        sa.CheckConstraint(_QUESTION_TYPE_CHECK, name=op.f("ck_interview_questions_question_type")),
        sa.CheckConstraint(_DIFFICULTY_CHECK, name=op.f("ck_interview_questions_difficulty")),
    )

    op.create_table(
        "interview_question_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("skill_name", sa.Text(), nullable=False, index=True),
        sa.Column("relevance_score", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"], name=op.f("fk_interview_question_skills_question_id_interview_questions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["skill_id"], ["skills.id"], name=op.f("fk_interview_question_skills_skill_id_skills"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_question_skills")),
    )

    op.create_table(
        "interview_turns",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("question_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("answer_text", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("difficulty", sa.String(length=10), nullable=True),
        sa.Column("evaluation_status", sa.String(length=20), nullable=False, server_default="PENDING"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], name=op.f("fk_interview_turns_session_id_interview_sessions"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["question_id"], ["interview_questions.id"], name=op.f("fk_interview_turns_question_id_interview_questions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_turns")),
        sa.CheckConstraint(_TURN_EVAL_STATUS_CHECK, name=op.f("ck_interview_turns_evaluation_status")),
    )

    op.create_table(
        "interview_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("correctness_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("depth_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("clarity_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("reasoning_score", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("strengths", sa.JSON(), nullable=True),
        sa.Column("weaknesses", sa.JSON(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["turn_id"], ["interview_turns.id"], name=op.f("fk_interview_evaluations_turn_id_interview_turns"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_evaluations")),
    )

    op.create_table(
        "interview_skill_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("skill_name", sa.Text(), nullable=False, index=True),
        sa.Column("questions_attempted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_score", sa.Float(), nullable=True),
        sa.Column("latest_score", sa.Float(), nullable=True),
        sa.Column("trend", sa.String(length=20), nullable=False, server_default="INSUFFICIENT_DATA"),
        sa.Column("performance_confidence", sa.Float(), nullable=True),
        sa.Column("evidence_metadata", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["interview_sessions.id"], name=op.f("fk_interview_skill_results_session_id_interview_sessions"), ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_skill_results")),
        sa.UniqueConstraint("session_id", "skill_name", name=op.f("uq_session_skill")),
        sa.CheckConstraint(_TREND_CHECK, name=op.f("ck_interview_skill_results_trend")),
    )


def downgrade() -> None:
    op.drop_table("interview_skill_results")
    op.drop_table("interview_evaluations")
    op.drop_table("interview_turns")
    op.drop_table("interview_question_skills")
    op.drop_table("interview_questions")
    op.drop_table("interview_sessions")
