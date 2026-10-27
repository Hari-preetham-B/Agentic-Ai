"""Initial career knowledge schema.

Create the curated career knowledge tables:

- careers
- career_skills
- career_tools
- career_projects
- career_sources

Revision ID: 0002_career_knowledge
Revises: 0001_initial_schema
Create Date: 2026-10-26
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002_career_knowledge"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_IMPORTANCE_CHECK = "importance IN ('CORE', 'IMPORTANT', 'SUPPORTING')"
_LEVEL_CHECK = "minimum_level IN ('BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT') OR minimum_level IS NULL"


def upgrade() -> None:
    op.create_table(
        "careers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("domain", sa.String(length=100), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "education_expectations",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "experience_expectations",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_careers")),
    )
    op.create_index(op.f("ix_careers_slug"), "careers", ["slug"], unique=True)

    op.create_table(
        "career_skills",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "career_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("skill_name", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column(
            "importance",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column("minimum_level", sa.String(length=20), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["career_id"],
            ["careers.id"],
            name=op.f("fk_career_skills_career_id_careers"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(_IMPORTANCE_CHECK, name=op.f("ck_career_skills_importance")),
        sa.CheckConstraint(_LEVEL_CHECK, name=op.f("ck_career_skills_minimum_level")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_skills")),
    )
    op.create_index(
        op.f("ix_career_skills_career_id"),
        "career_skills",
        ["career_id"],
        unique=False,
    )

    op.create_table(
        "career_tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "career_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column(
            "importance",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["career_id"],
            ["careers.id"],
            name=op.f("fk_career_tools_career_id_careers"),
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            _IMPORTANCE_CHECK, name=op.f("ck_career_tools_importance")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_tools")),
    )
    op.create_index(
        op.f("ix_career_tools_career_id"),
        "career_tools",
        ["career_id"],
        unique=False,
    )

    op.create_table(
        "career_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "career_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("project_type", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "skills_demonstrated",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column("difficulty", sa.String(length=20), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["career_id"],
            ["careers.id"],
            name=op.f("fk_career_projects_career_id_careers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_projects")),
    )
    op.create_index(
        op.f("ix_career_projects_career_id"),
        "career_projects",
        ["career_id"],
        unique=False,
    )

    op.create_table(
        "career_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "career_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("publisher", sa.String(length=200), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reliability", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["career_id"],
            ["careers.id"],
            name=op.f("fk_career_sources_career_id_careers"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_career_sources")),
    )
    op.create_index(
        op.f("ix_career_sources_career_id"),
        "career_sources",
        ["career_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("career_sources")
    op.drop_table("career_projects")
    op.drop_table("career_tools")
    op.drop_table("career_skills")
    op.drop_table("careers")
