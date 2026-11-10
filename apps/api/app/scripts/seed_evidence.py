"""Seed the curated evidence corpus idempotently.

Usage:
    cd apps/api
    python -m app.scripts.seed_evidence

The corpus lives in ``app/scripts/evidence_corpus.py``. Ingestion is
deterministic: documents are deduplicated by normalized checksum and sources
by URL (or publisher+title for sources without a URL), so rerunning the
command does not duplicate rows.

Embeddings use ``FakeEmbeddingProvider`` so the seeded vectors match the
default retrieval provider when no embedding API key is configured. The
provider abstraction remains unchanged for deployments that configure a real
embedding provider and re-embed the corpus.
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.embedding import FakeEmbeddingProvider
from app.models.evidence import (
    EvidenceChunk,
    EvidenceDocument,
    EvidenceSource,
)
from app.scripts.evidence_corpus import EVIDENCE_SOURCES
from app.services.evidence_ingestion_service import EvidenceIngestionService

EXPECTED_ALEMBIC_HEAD = "0006_row_level_security"


async def seed_evidence() -> dict[str, int]:
    """Ingest the curated corpus. Returns counts per table."""
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured — cannot seed evidence data"
        )

    from app.core.database import engine_kwargs

    engine = create_async_engine(
        settings.database_url, **engine_kwargs(settings.database_url)
    )
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    counts: dict[str, int] = {}
    try:
        async with factory() as session:
            result = await session.execute(
                text("SELECT version_num FROM alembic_version")
            )
            row = result.fetchone()
            if row is None or row[0] != EXPECTED_ALEMBIC_HEAD:
                raise RuntimeError(
                    "Database is not at the expected Alembic head "
                    f"({EXPECTED_ALEMBIC_HEAD}). Run 'alembic upgrade head'."
                )

            ingestion = EvidenceIngestionService(
                session, embedding_provider=FakeEmbeddingProvider()
            )

            for source in EVIDENCE_SOURCES:
                source_record = await ingestion.ingest_source(
                    source_type=source["source_type"],
                    title=source["title"],
                    publisher=source["publisher"],
                    url=source["url"],
                    published_at=source.get("published_at"),
                    reliability_score=source.get("reliability_score"),
                    metadata={"corpus": "careertwin-curated-career-knowledge-v1"},
                )
                for document in source.get("documents", []):
                    await ingestion.ingest_document(
                        source_id=str(source_record.id),
                        document_type=document["document_type"],
                        title=document["title"],
                        content=document["content"],
                        metadata={"slug": source["slug"]},
                    )

            # Recompute chunk embeddings so the corpus always matches the
            # deterministic embedding provider used for retrieval. This also
            # lets the command repair vectors written by older providers.
            provider = FakeEmbeddingProvider()
            dialect = session.get_bind().dialect.name
            chunk_result = await session.execute(select(EvidenceChunk))
            chunks = list(chunk_result.scalars().all())
            for chunk in chunks:
                vector = await provider.embed_text(chunk.content)
                if dialect == "postgresql":
                    chunk.embedding = [float(v) for v in vector]
                else:
                    import struct

                    chunk.embedding = struct.pack(
                        f"<{len(vector)}f", *vector
                    )
            await session.commit()

            for name, model in (
                ("evidence_sources", EvidenceSource),
                ("evidence_documents", EvidenceDocument),
                ("evidence_chunks", EvidenceChunk),
            ):
                n = await session.execute(select(model))
                counts[name] = len(n.scalars().all())
    finally:
        await engine.dispose()

    return counts


def main() -> None:
    try:
        counts = asyncio.run(seed_evidence())
    except Exception as exc:  # noqa: BLE001
        print(f"EVIDENCE SEED FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Evidence seed complete.")
    print("=" * 40)
    for table, count in counts.items():
        print(f"  {table}: {count}")
    print("=" * 40)
    print("Seed is idempotent — safe to rerun.")


if __name__ == "__main__":
    main()
