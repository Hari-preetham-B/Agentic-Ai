"""SQLAlchemy models for evidence intelligence.

These models store evidence sources, documents, chunks, claims, and claim-evidence
linkages. They are persistence models only; Pydantic schemas serve as the public
API contract.

Types are dialect-agnostic so tests can run against SQLite in-memory. The
Alembic migration uses PostgreSQL-specific types (pgvector) for production.

Note: The 'metadata' attribute is named 'metadata_' in Python (SQLAlchemy
convention for reserved words) but maps to the 'metadata' column in the database.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, created_at, uuid_pk


def sa_json():
    """Return a JSON column type portable across SQLite and PostgreSQL."""
    from sqlalchemy import JSON

    return JSON()


def embedding_column_type():
    """Embedding column type: pgvector on PostgreSQL, bytes on SQLite.

    The Alembic migration creates ``vector(384)`` on PostgreSQL. The ORM model
    must use the same type, otherwise inserts are sent as ``bytea`` and are
    rejected by the database. Tests on SQLite keep using ``LargeBinary``.
    """
    try:
        from pgvector.sqlalchemy import Vector

        return LargeBinary().with_variant(Vector(384), "postgresql")
    except ImportError:  # pragma: no cover - pgvector missing
        return LargeBinary()


class EvidenceSource(Base):
    """A source of evidence (e.g. O*NET, BLS, user document, curated knowledge)."""

    __tablename__ = "evidence_sources"

    id: Mapped[uuid_pk]
    source_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publisher: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reliability_score: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )
    created_at: Mapped[created_at]

    documents: Mapped[List["EvidenceDocument"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class EvidenceDocument(Base):
    """A document within an evidence source."""

    __tablename__ = "evidence_documents"

    id: Mapped[uuid_pk]
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("evidence_sources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )
    created_at: Mapped[created_at]

    source: Mapped["EvidenceSource"] = relationship(back_populates="documents")
    chunks: Mapped[List["EvidenceChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class EvidenceChunk(Base):
    """A text chunk within an evidence document, with optional vector embedding."""

    __tablename__ = "evidence_chunks"

    id: Mapped[uuid_pk]
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("evidence_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )
    embedding: Mapped[Optional[bytes]] = mapped_column(
        embedding_column_type(), nullable=True
    )
    created_at: Mapped[created_at]

    document: Mapped["EvidenceDocument"] = relationship(back_populates="chunks")


class Claim(Base):
    """A claim extracted from generated text, awaiting or having verification."""

    __tablename__ = "claims"

    id: Mapped[uuid_pk]
    profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, nullable=True, index=True
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    created_at: Mapped[created_at]

    evidence_links: Mapped[List["ClaimEvidence"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class ClaimEvidence(Base):
    """Linkage between a claim and an evidence chunk, with support/contradiction scores."""

    __tablename__ = "claim_evidence"

    id: Mapped[uuid_pk]
    claim_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    evidence_chunk_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("evidence_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_: Mapped[str] = mapped_column(
        "relationship", String(20), nullable=False
    )
    support_score: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    contradiction_score: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2), nullable=True
    )
    metadata_: Mapped[Optional[dict]] = mapped_column(
        "metadata", sa_json(), nullable=True
    )

    claim: Mapped["Claim"] = relationship(back_populates="evidence_links")
    evidence_chunk: Mapped["EvidenceChunk"] = relationship()


__all__ = [
    "EvidenceSource",
    "EvidenceDocument",
    "EvidenceChunk",
    "Claim",
    "ClaimEvidence",
]
