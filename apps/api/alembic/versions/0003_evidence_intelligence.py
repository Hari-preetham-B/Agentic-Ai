"""Evidence intelligence schema.

Create the evidence intelligence tables:

- evidence_sources
- evidence_documents
- evidence_chunks
- claims
- claim_evidence

Revision ID: 0003_evidence_intelligence
Revises: 0002_career_knowledge
Create Date: 2026-10-27
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# pgvector extension for PostgreSQL vector similarity search.
try:
    from pgvector.sqlalchemy import Vector

    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None

# revision identifiers, used by Alembic.
revision: str = "0003_evidence_intelligence"
down_revision: Union[str, None] = "0002_career_knowledge"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enforced status values for claims.
_CLAIM_STATUS_CHECK = (
    "status IN ('SUPPORTED', 'INFERRED', 'UNCERTAIN', 'CONTRADICTED')"
)

# Enforced relationship values for claim-evidence links.
_CLAIM_EVIDENCE_RELATIONSHIP_CHECK = (
    "relationship IN ('SUPPORTS', 'CONTRADICTS', 'CONTEXTUAL')"
)

# Enforced source type values.
_SOURCE_TYPE_CHECK = (
    "source_type IN ('USER_CONFIRMED', 'USER_DOCUMENT', 'CURATED_KNOWLEDGE', "
    "'RETRIEVED_EXTERNAL', 'LLM_INFERENCE')"
)

# Enforced document type values.
_DOCUMENT_TYPE_CHECK = (
    "document_type IN ('OCCUPATIONAL_PROFILE', 'SKILL_DEFINITION', "
    "'INDUSTRY_REPORT', 'STANDARD_DOCUMENT', 'USER_RESUME', 'OTHER')"
)


def upgrade() -> None:
    # Enable pgvector extension if available (PostgreSQL only).
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    op.create_table(
        "evidence_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_type",
            sa.String(length=50),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "publisher", sa.String(length=200), nullable=False
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "retrieved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "reliability_score",
            sa.Numeric(3, 2),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_sources")),
        sa.CheckConstraint(_SOURCE_TYPE_CHECK, name=op.f("ck_evidence_sources_source_type")),
    )

    op.create_table(
        "evidence_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "document_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "checksum",
            sa.String(length=64),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["evidence_sources.id"],
            name=op.f("fk_evidence_documents_source_id_evidence_sources"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_documents")),
        sa.CheckConstraint(
            _DOCUMENT_TYPE_CHECK,
            name=op.f("ck_evidence_documents_document_type"),
        ),
    )

    op.create_table(
        "evidence_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "embedding",
            # pgvector Vector type for PostgreSQL semantic similarity search.
            # Dimension 384 matches the FakeEmbeddingProvider output dimension.
            # In production, embeddings are stored as pgvector Vector(384).
            # In tests (SQLite), stored as LargeBinary.
            (
                sa.LargeBinary().with_variant(Vector(384), "postgresql")
                if PGVECTOR_AVAILABLE
                else sa.LargeBinary()
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["evidence_documents.id"],
            name=op.f("fk_evidence_chunks_document_id_evidence_documents"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evidence_chunks")),
    )

    op.create_table(
        "claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            index=True,
        ),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column(
            "claim_type",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "confidence_score",
            sa.Numeric(3, 2),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claims")),
        sa.CheckConstraint(_CLAIM_STATUS_CHECK, name=op.f("ck_claims_status")),
    )

    op.create_table(
        "claim_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "claim_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "evidence_chunk_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "relationship",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "support_score",
            sa.Numeric(3, 2),
            nullable=True,
        ),
        sa.Column(
            "contradiction_score",
            sa.Numeric(3, 2),
            nullable=True,
        ),
        sa.Column(
            "metadata",
            sa.JSON(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["claim_id"],
            ["claims.id"],
            name=op.f("fk_claim_evidence_claim_id_claims"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_chunk_id"],
            ["evidence_chunks.id"],
            name=op.f("fk_claim_evidence_evidence_chunk_id_evidence_chunks"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claim_evidence")),
        sa.CheckConstraint(
            _CLAIM_EVIDENCE_RELATIONSHIP_CHECK,
            name=op.f("ck_claim_evidence_relationship"),
        ),
    )


def downgrade() -> None:
    op.drop_table("claim_evidence")
    op.drop_table("claims")
    op.drop_table("evidence_chunks")
    op.drop_table("evidence_documents")
    op.drop_table("evidence_sources")
