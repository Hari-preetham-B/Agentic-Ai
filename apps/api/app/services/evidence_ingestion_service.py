"""Evidence ingestion service.

Responsibilities:

- accept curated documents
- normalize content
- calculate checksum
- avoid duplicate documents (checksum-based idempotency)
- chunk documents deterministically
- preserve source metadata
- generate embeddings
- persist documents/chunks

Chunking is deterministic — no LLM involvement. Configurable chunk size and
overlap.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.core.database import get_session_factory
from app.core.embedding import FakeEmbeddingProvider, EmbeddingProvider
from app.models.evidence import (
    EvidenceChunk,
    EvidenceDocument,
    EvidenceSource,
)
from app.services.repositories import EvidenceRepository
from sqlalchemy.ext.asyncio import AsyncSession


class EvidenceIngestionService:
    """Service for ingesting evidence documents deterministically."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> None:
        self.session = session
        self.repo = EvidenceRepository(session)
        self.embedding_provider = embedding_provider or FakeEmbeddingProvider()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ingest_source(
        self,
        *,
        source_type: str,
        title: str,
        publisher: str,
        url: str | None = None,
        published_at: Any | None = None,
        retrieved_at: Any | None = None,
        reliability_score: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceSource:
        """Create or retrieve an evidence source."""
        source = EvidenceSource(
            source_type=source_type,
            title=title,
            publisher=publisher,
            url=url,
            published_at=published_at,
            retrieved_at=retrieved_at,
            reliability_score=reliability_score,
            metadata_=metadata,
        )
        return await self.repo.create_source(source)

    async def ingest_document(
        self,
        *,
        source_id: str,
        document_type: str,
        title: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceDocument:
        """Ingest a document with deduplication by checksum.

        Returns the existing document if one with the same checksum already
        exists (idempotent).
        """
        checksum = self._calculate_checksum(content)

        existing = await self.repo.get_document_by_checksum(checksum)
        if existing is not None:
            return existing

        document = EvidenceDocument(
            source_id=source_id,
            document_type=document_type,
            title=title,
            content=content,
            checksum=checksum,
            metadata_=metadata,
        )
        document = await self.repo.create_document(document)

        # Chunk and embed the document.
        chunks = self._chunk_text(content, document.id)
        for chunk in chunks:
            embedding = await self.embedding_provider.embed_text(
                chunk.content
            )
            chunk.embedding = self._serialize_embedding(embedding)
            await self.repo.create_chunk(chunk)

        return document

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_checksum(content: str) -> str:
        """Return a SHA-256 checksum of the normalized content."""
        normalized = re.sub(r"\s+", " ", content.strip()).lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _chunk_text(
        self,
        content: str,
        document_id: str,
    ) -> list[EvidenceChunk]:
        """Deterministically split content into overlapping chunks.

        Strategy:
        - Split on sentence boundaries where possible.
        - Target chunk_size characters per chunk.
        - Overlap by chunk_overlap characters between consecutive chunks.
        """
        chunks: list[EvidenceChunk] = []
        text = content.strip()
        if not text:
            return chunks

        size = self.chunk_size
        overlap = self.chunk_overlap

        start = 0
        index = 0
        while start < len(text):
            end = min(start + size, len(text))

            # Try to break on a sentence boundary near the end.
            if end < len(text):
                sentence_end = _find_sentence_boundary(text, start, end)
                if sentence_end is not None and sentence_end > start:
                    end = sentence_end

            chunk_text = text[start:end].strip()
            if not chunk_text:
                break

            chunks.append(
                EvidenceChunk(
                    document_id=document_id,
                    chunk_index=index,
                    content=chunk_text,
                )
            )
            index += 1

            if end >= len(text):
                break
            start = max(start + 1, end - overlap)

        return chunks

    @staticmethod
    def _serialize_embedding(embedding: list[float]) -> bytes:
        """Serialize a float embedding to bytes for storage."""
        import struct

        return struct.pack(f"<{len(embedding)}f", *embedding)


def _find_sentence_boundary(text: str, start: int, end: int) -> int | None:
    """Find the last sentence-ending punctuation within [start, end]."""
    # Look backward from end for ., !, ? followed by whitespace or end.
    for i in range(min(end, len(text)) - 1, start - 1, -1):
        if text[i] in ".!?":
            if i + 1 >= len(text) or text[i + 1] in " \n\t":
                return i + 1
    return None


__all__ = ["EvidenceIngestionService"]
