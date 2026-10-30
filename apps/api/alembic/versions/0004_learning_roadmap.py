"""Learning intelligence and career roadmap schema.

Create the learning intelligence tables:

- learning_resources
- skill_dependencies
- learning_resource_skills
- roadmaps
- roadmap_items
- roadmap_resources

Revision ID: 0004_learning_roadmap
Revises: 0003_evidence_intelligence
Create Date: 2026-10-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0004_learning_roadmap"
down_revision: Union[str, None] = "0003_evidence_intelligence"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RESOURCE_TYPE_CHECK = (
    "resource_type IN ('COURSE', 'TUTORIAL', 'DOCUMENTATION', 'BOOK', "
    "'PROJECT', 'PRACTICE', 'VIDEO')"
)

_DIFFICULTY_CHECK = (
    "difficulty IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT') OR difficulty IS NULL"
)

_ROADMAP_STATUS_CHECK = (
    "status IN ('GENERATED', 'IN_PROGRESS', 'COMPLETED', 'ARCHIVED')"
)

_ROADMAP_ITEM_STATUS_CHECK = (
    "status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'SKIPPED')"
)

_PRIORITY_CHECK = "priority IN ('P0', 'P1', 'P2')"


def upgrade() -> None:
    op.create_table(
        "learning_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=200), nullable=False),
        sa.Column("resource_type", sa.String(length=50), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column("estimated_hours", sa.Float(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_resources")),
        sa.CheckConstraint(_RESOURCE_TYPE_CHECK, name=op.f("ck_learning_resources_resource_type")),
        sa.CheckConstraint(_DIFFICULTY_CHECK, name=op.f("ck_learning_resources_difficulty")),
    )

    op.create_table(
        "skill_dependencies",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "skill_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "prerequisite_skill_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "strength",
            sa.String(length=20),
            nullable=False,
            server_default="REQUIRED",
        ),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["skill_id"],
            ["skills.id"],
            name=op.f("fk_skill_dependencies_skill_id_skills"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prerequisite_skill_id"],
            ["skills.id"],
            name=op.f("fk_skill_dependencies_prerequisite_skill_id_skills"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill_dependencies")),
        sa.UniqueConstraint(
            "skill_id", "prerequisite_skill_id",
            name=op.f("uq_skill_dependency"),
        ),
        sa.CheckConstraint(
            "skill_id != prerequisite_skill_id",
            name=op.f("ck_skill_dependencies_no_self"),
        ),
    )

    op.create_table(
        "learning_resource_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "skill_name",
            sa.Text(),
            nullable=False,
            index=True,
        ),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("coverage_type", sa.String(length=50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["learning_resources.id"],
            name=op.f("fk_learning_resource_skills_resource_id_learning_resources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_resource_skills")),
    )

    op.create_table(
        "roadmaps",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "career_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="GENERATED",
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["profiles.id"],
            name=op.f("fk_roadmaps_profile_id_profiles"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["career_id"],
            ["careers.id"],
            name=op.f("fk_roadmaps_career_id_careers"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roadmaps")),
        sa.CheckConstraint(_ROADMAP_STATUS_CHECK, name=op.f("ck_roadmaps_status")),
    )

    op.create_table(
        "roadmap_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "roadmap_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column("skill_name", sa.Text(), nullable=False),
        sa.Column(
            "priority",
            sa.String(length=5),
            nullable=False,
            server_default="P2",
        ),
        sa.Column(
            "sequence_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("estimated_hours", sa.Float(), nullable=True),
        sa.Column("current_proficiency", sa.String(length=20), nullable=True),
        sa.Column("target_proficiency", sa.String(length=20), nullable=True),
        sa.Column("prerequisites", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["roadmap_id"],
            ["roadmaps.id"],
            name=op.f("fk_roadmap_items_roadmap_id_roadmaps"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roadmap_items")),
        sa.CheckConstraint(_PRIORITY_CHECK, name=op.f("ck_roadmap_items_priority")),
        sa.CheckConstraint(_ROADMAP_ITEM_STATUS_CHECK, name=op.f("ck_roadmap_items_status")),
    )

    op.create_table(
        "roadmap_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "roadmap_item_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column("relevance_score", sa.Float(), nullable=True),
        sa.Column("sequence_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["roadmap_item_id"],
            ["roadmap_items.id"],
            name=op.f("fk_roadmap_resources_roadmap_item_id_roadmap_items"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resource_id"],
            ["learning_resources.id"],
            name=op.f("fk_roadmap_resources_resource_id_learning_resources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roadmap_resources")),
    )


def downgrade() -> None:
    op.drop_table("roadmap_resources")
    op.drop_table("roadmap_items")
    op.drop_table("roadmaps")
    op.drop_table("learning_resource_skills")
    op.drop_table("skill_dependencies")
    op.drop_table("learning_resources")
