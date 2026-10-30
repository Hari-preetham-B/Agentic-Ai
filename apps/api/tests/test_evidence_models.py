"""Tests for evidence models and repository."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import (
    Claim,
    ClaimEvidence,
    EvidenceChunk,
    EvidenceDocument,
    EvidenceSource,
)
from app.services.repositories import EvidenceRepository


@pytest_asyncio.fixture
async def seeded_source(session: AsyncSession) -> EvidenceSource:
    repo = EvidenceRepository(session)
    source = EvidenceSource(
        source_type="CURATED_KNOWLEDGE",
        title="Test Source",
        publisher="Test Publisher",
        url="https://example.com",
        reliability_score=0.9,
    )
    return await repo.create_source(source)


@pytest_asyncio.fixture
async def seeded_document(
    session: AsyncSession, seeded_source: EvidenceSource
) -> EvidenceDocument:
    repo = EvidenceRepository(session)
    document = EvidenceDocument(
        source_id=seeded_source.id,
        document_type="OCCUPATIONAL_PROFILE",
        title="Test Document",
        content="Python is a core skill for software engineers.",
        checksum="abc123",
    )
    return await repo.create_document(document)


@pytest_asyncio.fixture
async def seeded_chunk(
    session: AsyncSession, seeded_document: EvidenceDocument
) -> EvidenceChunk:
    repo = EvidenceRepository(session)
    chunk = EvidenceChunk(
        document_id=seeded_document.id,
        chunk_index=0,
        content="Python is a core skill.",
        embedding=b"\x00" * 12,
    )
    return await repo.create_chunk(chunk)


@pytest.mark.asyncio
async def test_evidence_source_crud(session: AsyncSession) -> None:
    repo = EvidenceRepository(session)
    source = EvidenceSource(
        source_type="USER_CONFIRMED",
        title="User Source",
        publisher="User",
        reliability_score=1.0,
    )
    created = await repo.create_source(source)
    assert created.id is not None
    assert created.source_type == "USER_CONFIRMED"
    assert created.title == "User Source"

    fetched = await repo.get_source(created.id)
    assert fetched is not None
    assert fetched.title == "User Source"

    sources = await repo.list_sources(source_type="USER_CONFIRMED")
    assert len(sources) >= 1


@pytest.mark.asyncio
async def test_evidence_document_crud(
    session: AsyncSession, seeded_source: EvidenceSource
) -> None:
    repo = EvidenceRepository(session)
    document = EvidenceDocument(
        source_id=seeded_source.id,
        document_type="SKILL_DEFINITION",
        title="Python Skill",
        content="Python is a programming language.",
        checksum="def456",
    )
    created = await repo.create_document(document)
    assert created.id is not None

    fetched = await repo.get_document(created.id)
    assert fetched is not None
    assert fetched.title == "Python Skill"

    by_checksum = await repo.get_document_by_checksum("def456")
    assert by_checksum is not None
    assert by_checksum.id == created.id

    docs = await repo.list_documents_by_source(seeded_source.id)
    assert len(docs) >= 1


@pytest.mark.asyncio
async def test_evidence_chunk_crud(
    session: AsyncSession, seeded_document: EvidenceDocument
) -> None:
    repo = EvidenceRepository(session)
    chunk = EvidenceChunk(
        document_id=seeded_document.id,
        chunk_index=0,
        content="Chunk content",
        embedding=b"\x01" * 12,
    )
    created = await repo.create_chunk(chunk)
    assert created.id is not None

    fetched = await repo.get_chunk(created.id)
    assert fetched is not None
    assert fetched.content == "Chunk content"

    chunks = await repo.list_chunks_by_document(seeded_document.id)
    assert len(chunks) >= 1


@pytest.mark.asyncio
async def test_claim_crud(session: AsyncSession) -> None:
    repo = EvidenceRepository(session)
    claim = Claim(
        profile_id=uuid.uuid4(),
        claim_text="Python is a core skill.",
        claim_type="skill_requirement",
        status="SUPPORTED",
        confidence_score=0.85,
    )
    created = await repo.create_claim(claim)
    assert created.id is not None
    assert created.status == "SUPPORTED"

    fetched = await repo.get_claim(created.id)
    assert fetched is not None
    assert fetched.claim_text == "Python is a core skill."


@pytest.mark.asyncio
async def test_claim_evidence_link(
    session: AsyncSession, seeded_claim: Claim, seeded_chunk: EvidenceChunk
) -> None:
    repo = EvidenceRepository(session)
    link = ClaimEvidence(
        claim_id=seeded_claim.id,
        evidence_chunk_id=seeded_chunk.id,
        relationship_="SUPPORTS",
        support_score=0.9,
        contradiction_score=None,
    )
    created = await repo.link_claim_evidence(link)
    assert created.id is not None

    links = await repo.get_claim_evidence(seeded_claim.id)
    assert len(links) >= 1
    assert links[0].relationship_ == "SUPPORTS"


@pytest_asyncio.fixture
async def seeded_claim(session: AsyncSession) -> Claim:
    repo = EvidenceRepository(session)
    claim = Claim(
        profile_id=uuid.uuid4(),
        claim_text="Python is a core skill.",
        claim_type="skill_requirement",
        status="SUPPORTED",
        confidence_score=0.85,
    )
    return await repo.create_claim(claim)


@pytest.mark.asyncio
async def test_evidence_model_constraints(session: AsyncSession) -> None:
    """Test that evidence models enforce required fields."""
    repo = EvidenceRepository(session)

    # Null required fields should fail at the database level.
    with pytest.raises(Exception):
        bad = EvidenceSource(
            source_type=None,
            title=None,
            publisher=None,
        )
        await repo.create_source(bad)
        await session.flush()


__all__ = [
    "test_evidence_source_crud",
    "test_evidence_document_crud",
    "test_evidence_chunk_crud",
    "test_claim_crud",
    "test_claim_evidence_link",
    "test_evidence_model_constraints",
]
