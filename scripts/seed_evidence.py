"""Seed curated evidence data for Phase 5 evidence intelligence.

Populates evidence_sources, evidence_documents, and evidence_chunks with
curated, sourced data from reputable occupational and technical sources.
The seed is idempotent — running it multiple times must not create duplicates
(deduplication by document checksum).

Usage:
    cd apps/api
    python ../scripts/seed_evidence.py   # requires DATABASE_URL in .env
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timezone

from app.core.database import create_all, get_engine, get_session_factory
from app.models.evidence import (
    EvidenceChunk,
    EvidenceDocument,
    EvidenceSource,
)
from app.services.evidence_ingestion_service import EvidenceIngestionService

# Deterministic UUID namespace for evidence records.
EVIDENCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def deterministic_id(name: str) -> uuid.UUID:
    return uuid.uuid5(EVIDENCE_NAMESPACE, name)


# ---------------------------------------------------------------------------
# Curated evidence dataset
# ---------------------------------------------------------------------------

EVIDENCE_DATA = [
    {
        "source_type": "CURATED_KNOWLEDGE",
        "title": "O*NET Software Developers Summary",
        "publisher": "U.S. Department of Labor, O*NET OnLine",
        "url": "https://www.onetonline.org/link/summary/15-1252.00",
        "published_at": date(2024, 1, 1),
        "reliability_score": 0.95,
        "document_type": "OCCUPATIONAL_PROFILE",
        "document_title": "Software Developers — O*NET Summary",
        "document_content": (
            "Software developers design, build, test, and maintain software "
            "applications and systems. Core skills include programming in "
            "languages such as Python, Java, and JavaScript; database querying "
            "with SQL; version control with Git; and software testing. "
            "Typical education includes a bachelor's degree in computer science "
            "or a related field. Entry-level positions typically require 0-2 "
            "years of experience."
        ),
    },
    {
        "source_type": "CURATED_KNOWLEDGE",
        "title": "BLS Software Developers Outlook",
        "publisher": "U.S. Bureau of Labor Statistics",
        "url": "https://www.bls.gov/ooh/computer-and-information-technology/software-developers.htm",
        "published_at": date(2024, 4, 25),
        "reliability_score": 0.98,
        "document_type": "OCCUPATIONAL_PROFILE",
        "document_title": "Software Developers — Occupational Outlook Handbook",
        "document_content": (
            "Employment of software developers is projected to grow 25 percent "
            "from 2022 to 2032, much faster than the average for all "
            "occupations. The median annual wage for software developers was "
            "$130,160 in May 2022. A bachelor's degree in computer and "
            "information technology or a related field is typically required."
        ),
    },
    {
        "source_type": "CURATED_KNOWLEDGE",
        "title": "Python Official Documentation",
        "publisher": "Python Software Foundation",
        "url": "https://docs.python.org/3/",
        "published_at": date(2024, 6, 1),
        "reliability_score": 0.99,
        "document_type": "STANDARD_DOCUMENT",
        "document_title": "Python 3 Documentation",
        "document_content": (
            "Python is an interpreted, object-oriented, high-level programming "
            "language with dynamic semantics. Its high-level built-in data "
            "structures, combined with dynamic typing and dynamic binding, make "
            "it very attractive for Rapid Application Development and for use "
            "as a scripting or glue language to connect existing components."
        ),
    },
    {
        "source_type": "CURATED_KNOWLEDGE",
        "title": "SQL Standard Documentation",
        "publisher": "ISO/IEC",
        "url": "https://www.iso.org/standard/63554.html",
        "published_at": date(2023, 6, 1),
        "reliability_score": 0.95,
        "document_type": "STANDARD_DOCUMENT",
        "document_title": "ISO/IEC 9075 SQL Standard",
        "document_content": (
            "SQL (Structured Query Language) is a domain-specific language used "
            "in programming and designed for managing data held in a relational "
            "database management system. It is particularly useful for handling "
            "structured data with relations between entities and variables."
        ),
    },
    {
        "source_type": "CURATED_KNOWLEDGE",
        "title": "O*NET Data Scientists Summary",
        "publisher": "U.S. Department of Labor, O*NET OnLine",
        "url": "https://www.onetonline.org/link/summary/15-2051.00",
        "published_at": date(2024, 1, 1),
        "reliability_score": 0.95,
        "document_type": "OCCUPATIONAL_PROFILE",
        "document_title": "Data Scientists — O*NET Summary",
        "document_content": (
            "Data scientists develop and implement analytical models to extract "
            "insights from data. Core skills include statistics, machine "
            "learning, Python programming, SQL, and data visualization. "
            "Typical entry-level education is a master's degree in a "
            "quantitative field such as statistics, mathematics, or computer "
            "science."
        ),
    },
    {
        "source_type": "CURATED_KNOWLEDGE",
        "title": "O*NET Cybersecurity Analysts Summary",
        "publisher": "U.S. Department of Labor, O*NET OnLine",
        "url": "https://www.onetonline.org/link/summary/15-1212.00",
        "published_at": date(2024, 1, 1),
        "reliability_score": 0.95,
        "document_type": "OCCUPATIONAL_PROFILE",
        "document_title": "Information Security Analysts — O*NET Summary",
        "document_content": (
            "Information security analysts plan and carry out security measures "
            "to protect an organization's computer networks and systems. Core "
            "skills include network security, incident response, vulnerability "
            "management, SIEM tools, and Linux administration. Certifications "
            "such as CompTIA Security+ are commonly expected."
        ),
    },
]


async def seed(session) -> None:
    """Ingest all curated evidence documents idempotently."""
    service = EvidenceIngestionService(session)

    for evidence in EVIDENCE_DATA:
        await service.ingest_source(
            source_type=evidence["source_type"],
            title=evidence["title"],
            publisher=evidence["publisher"],
            url=evidence["url"],
            published_at=evidence["published_at"],
            retrieved_at=datetime.now(timezone.utc),
            reliability_score=evidence["reliability_score"],
        )

        # Get the source ID to link documents.
        from app.services.repositories import EvidenceRepository

        repo = EvidenceRepository(session)
        sources = await repo.list_sources(source_type=evidence["source_type"])
        # Find the source by title.
        source = next((s for s in sources if s.title == evidence["title"]), None)
        if source is None:
            raise RuntimeError(f"Source not found after creation: {evidence['title']}")

        await service.ingest_document(
            source_id=str(source.id),
            document_type=evidence["document_type"],
            title=evidence["document_title"],
            content=evidence["document_content"],
        )

    await session.commit()

    # Print summary.
    repo = EvidenceRepository(session)
    sources = await repo.list_sources()
    docs = 0
    chunks = 0
    for s in sources:
        s_docs = await repo.list_documents_by_source(s.id)
        docs += len(s_docs)
        for d in s_docs:
            s_chunks = await repo.list_chunks_by_document(d.id)
            chunks += len(s_chunks)

    print("Evidence seed complete.")
    print(f"  Sources: {len(sources)}")
    print(f"  Documents: {docs}")
    print(f"  Chunks: {chunks}")


async def main() -> None:
    await create_all()
    factory = get_session_factory()
    async with factory() as session:
        await seed(session)


if __name__ == "__main__":
    asyncio.run(main())
