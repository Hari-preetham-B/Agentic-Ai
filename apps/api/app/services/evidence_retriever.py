"""Evidence retriever.

Performs semantic similarity retrieval using pgvector embeddings stored in
evidence_chunks. Supports metadata filtering, source-type filtering, top-K
retrieval, and minimum similarity thresholds.

All retrieval results include full provenance (chunk, document, source).
"""

from __future__ import annotations

import math
import struct
from typing import Any

from app.core.embedding import FakeEmbeddingProvider, EmbeddingProvider
from app.models.evidence import (
    EvidenceChunk,
    EvidenceDocument,
    EvidenceSource,
)
from app.services.repositories import EvidenceRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class ChunkResult:
    """A retrieved evidence chunk with full provenance."""

    def __init__(
        self,
        *,
        chunk_id: str,
        document_id: str,
        source_id: str,
        source_type: str,
        title: str,
        publisher: str,
        url: str | None,
        similarity_score: float,
        content: str,
        chunk_index: int,
    ) -> None:
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.source_id = source_id
        self.source_type = source_type
        self.title = title
        self.publisher = publisher
        self.url = url
        self.similarity_score = similarity_score
        self.content = content
        self.chunk_index = chunk_index

    def model_dump(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "source_id": self.source_id,
            "source_type": self.source_type,
            "title": self.title,
            "publisher": self.publisher,
            "url": self.url,
            "similarity_score": round(self.similarity_score, 4),
            "content": self.content,
            "chunk_index": self.chunk_index,
        }


class EvidenceRetriever:
    """Retrieves evidence chunks via semantic similarity search."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.repo = EvidenceRepository(session)
        self.embedding_provider = embedding_provider or FakeEmbeddingProvider()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        *,
        query: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
        source_type: str | None = None,
        document_type: str | None = None,
    ) -> list[ChunkResult]:
        """Retrieve chunks most similar to the query.

        Uses cosine similarity between the query embedding and stored chunk
        embeddings. Falls back to keyword matching when no embeddings are
        available (e.g. SQLite in tests).
        """
        query_embedding = await self.embedding_provider.embed_text(query)
        query_bytes = self._serialize_embedding(query_embedding)

        # Check if we're on PostgreSQL (production) or SQLite (tests).
        try:
            bind = self.session.get_bind()
            dialect_name = bind.dialect.name
        except Exception:
            dialect_name = "sqlite"
        dialect = dialect_name

        if dialect == "postgresql":
            # Use pgvector's cosine distance operator for native vector search.
            return await self._pgvector_search(
                query=query,
                query_embedding=query_embedding,
                top_k=top_k,
                min_similarity=min_similarity,
                source_type=source_type,
                document_type=document_type,
            )

        # SQLite fallback: Python-based cosine similarity (test-only).
        chunks = await self._fetch_chunks(
            source_type=source_type,
            document_type=document_type,
        )

        # Score each chunk.
        scored: list[tuple[float, EvidenceChunk, EvidenceDocument, EvidenceSource]] = []
        for chunk, document, source in chunks:
            if chunk.embedding is None:
                continue
            similarity = self._cosine_similarity(query_bytes, chunk.embedding)
            if similarity < min_similarity:
                continue
            scored.append((similarity, chunk, document, source))

        # Sort by similarity descending and take top-K.
        # Tie-break by chunk_id for deterministic ordering.
        scored.sort(key=lambda x: (-x[0], str(x[1].id)))
        top = scored[:top_k]

        return [
            ChunkResult(
                chunk_id=str(chunk.id),
                document_id=str(document.id),
                source_id=str(source.id),
                source_type=source.source_type,
                title=document.title,
                publisher=source.publisher,
                url=source.url,
                similarity_score=similarity,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
            )
            for similarity, chunk, document, source in top
        ]

    async def _pgvector_search(
        self,
        *,
        query: str,
        query_embedding: list[float],
        top_k: int,
        min_similarity: float,
        source_type: str | None,
        document_type: str | None,
    ) -> list[ChunkResult]:
        """Use pgvector's cosine distance operator for native vector search.

        This is the production code path. It uses PostgreSQL's pgvector
        extension for efficient approximate nearest-neighbor search.
        """
        from sqlalchemy import text as sa_text

        sql = sa_text(
            "SELECT "
            "ec.id AS chunk_id, "
            "ec.document_id AS document_id, "
            "ed.source_id AS source_id, "
            "es.source_type AS source_type, "
            "ed.title AS title, "
            "es.publisher AS publisher, "
            "es.url AS url, "
            "(1 - (ec.embedding <=> :query_vec)) AS similarity_score, "
            "ec.content AS content, "
            "ec.chunk_index AS chunk_index "
            "FROM evidence_chunks ec "
            "JOIN evidence_documents ed ON ec.document_id = ed.id "
            "JOIN evidence_sources es ON ed.source_id = es.id "
            "WHERE ec.embedding IS NOT NULL "
            "AND (:source_type IS NULL OR es.source_type = :source_type) "
            "AND (:document_type IS NULL OR ed.document_type = :document_type) "
            "AND (1 - (ec.embedding <=> :query_vec)) >= :min_similarity "
            "ORDER BY ec.embedding <=> :query_vec "
            "LIMIT :top_k"
        )

        result = await self.session.execute(
            sql,
            {
                "query_vec": str(query_embedding),
                "source_type": source_type,
                "document_type": document_type,
                "min_similarity": min_similarity,
                "top_k": top_k,
            },
        )

        rows = result.fetchall()
        return [
            ChunkResult(
                chunk_id=str(row.chunk_id),
                document_id=str(row.document_id),
                source_id=str(row.source_id),
                source_type=row.source_type,
                title=row.title,
                publisher=row.publisher,
                url=row.url,
                similarity_score=float(row.similarity_score),
                content=row.content,
                chunk_index=int(row.chunk_index),
            )
            for row in rows
        ]

    async def get_chunk(self, chunk_id: str) -> ChunkResult | None:
        """Retrieve a single chunk by ID with provenance."""
        import uuid

        chunk = await self.repo.get_chunk(uuid.UUID(chunk_id))
        if chunk is None:
            return None
        document = await self.repo.get_document(chunk.document_id)
        if document is None:
            return None
        source = await self.repo.get_source(document.source_id)
        if source is None:
            return None
        return ChunkResult(
            chunk_id=str(chunk.id),
            document_id=str(document.id),
            source_id=str(source.id),
            source_type=source.source_type,
            title=document.title,
            publisher=source.publisher,
            url=source.url,
            similarity_score=1.0,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _fetch_chunks(
        self,
        *,
        source_type: str | None = None,
        document_type: str | None = None,
    ) -> list[tuple[EvidenceChunk, EvidenceDocument, EvidenceSource]]:
        """Fetch all chunks with their documents and sources."""
        stmt = (
            select(EvidenceChunk, EvidenceDocument, EvidenceSource)
            .join(EvidenceDocument, EvidenceChunk.document_id == EvidenceDocument.id)
            .join(EvidenceSource, EvidenceDocument.source_id == EvidenceSource.id)
            .where(EvidenceChunk.embedding.is_not(None))
        )
        if source_type:
            stmt = stmt.where(EvidenceSource.source_type == source_type)
        if document_type:
            stmt = stmt.where(EvidenceDocument.document_type == document_type)

        result = await self.session.execute(stmt)
        return list(result.all())

    @staticmethod
    def _serialize_embedding(embedding: list[float]) -> bytes:
        """Serialize a float embedding to bytes for storage/comparison."""
        return struct.pack(f"<{len(embedding)}f", *embedding)

    @staticmethod
    def _cosine_similarity(a: bytes, b: bytes) -> float:
        """Compute cosine similarity between two serialized float vectors."""
        if len(a) != len(b):
            return 0.0

        # Unpack bytes to floats.
        n = len(a) // 4
        va = struct.unpack(f"<{n}f", a)
        vb = struct.unpack(f"<{n}f", b)

        dot = sum(x * y for x, y in zip(va, vb))
        norm_a = math.sqrt(sum(x * x for x in va))
        norm_b = math.sqrt(sum(x * x for x in vb))

        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0

        return dot / (norm_a * norm_b)


__all__ = ["EvidenceRetriever", "ChunkResult"]
