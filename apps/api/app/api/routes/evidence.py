"""Evidence intelligence API routes.

Endpoints:
- GET /evidence/search — search evidence chunks by semantic similarity
- POST /claims/verify — verify a claim against stored evidence
- GET /claims/{claim_id} — get a verified claim
- GET /claims/{claim_id}/evidence — get evidence linked to a claim
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.claim_verification_service import ClaimVerificationService
from app.services.evidence_ingestion_service import EvidenceIngestionService
from app.services.evidence_retriever import EvidenceRetriever
from app.services.repositories import EvidenceRepository

router = APIRouter(tags=["evidence"])


# ---------------------------------------------------------------------------
# Evidence search
# ---------------------------------------------------------------------------


class EvidenceSearchRequest(BaseModel):
    query: str = Field(..., description="Search query text.")
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    source_type: str | None = Field(default=None)


class EvidenceSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    source_id: str
    source_type: str
    title: str
    publisher: str
    url: str | None = None
    similarity_score: float
    content: str
    chunk_index: int


class EvidenceSearchResponse(BaseModel):
    results: list[EvidenceSearchResult]


@router.post(
    "/evidence/search",
    response_model=EvidenceSearchResponse,
    summary="Search evidence chunks by semantic similarity",
)
async def search_evidence(
    request: EvidenceSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> EvidenceSearchResponse:
    retriever = EvidenceRetriever(session)
    results = await retriever.search(
        query=request.query,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        source_type=request.source_type,
    )
    return EvidenceSearchResponse(
        results=[EvidenceSearchResult(**r.model_dump()) for r in results]
    )


# ---------------------------------------------------------------------------
# Claim verification
# ---------------------------------------------------------------------------


class ClaimVerifyRequest(BaseModel):
    claim_text: str = Field(..., description="The claim text to verify.")
    claim_type: str = Field(default="other")
    importance: str = Field(default="SUPPORTING")
    profile_id: str | None = Field(default=None)
    context: str | None = Field(default=None)


class ClaimVerifyResponse(BaseModel):
    claim: str
    claim_type: str
    importance: str
    status: str
    confidence: float
    evidence: list[dict] = Field(default_factory=list)
    contradictions: list[dict] = Field(default_factory=list)
    explanation: str
    factors: dict[str, Any] = Field(default_factory=dict)


@router.post(
    "/claims/verify",
    response_model=ClaimVerifyResponse,
    summary="Verify a claim against stored evidence deterministically",
)
async def verify_claim(
    request: ClaimVerifyRequest,
    session: AsyncSession = Depends(get_session),
) -> ClaimVerifyResponse:
    service = ClaimVerificationService(session)
    result = await service.verify_single_claim_text(
        claim_text=request.claim_text,
        claim_type=request.claim_type,
        importance=request.importance,
        profile_id=request.profile_id,
        context=request.context,
    )
    return ClaimVerifyResponse(**result.model_dump())


# ---------------------------------------------------------------------------
# Claim retrieval
# ---------------------------------------------------------------------------


class ClaimResponse(BaseModel):
    id: str
    profile_id: str | None = None
    claim_text: str
    claim_type: str
    status: str
    confidence_score: float | None = None
    created_at: str


@router.get(
    "/claims/{claim_id}",
    response_model=ClaimResponse,
    summary="Get a verified claim by ID",
)
async def get_claim(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> ClaimResponse:
    repo = EvidenceRepository(session)
    import uuid

    claim = await repo.get_claim(UUID(claim_id))
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found"
        )
    return ClaimResponse(
        id=str(claim.id),
        profile_id=str(claim.profile_id) if claim.profile_id else None,
        claim_text=claim.claim_text,
        claim_type=claim.claim_type,
        status=claim.status,
        confidence_score=(
            float(claim.confidence_score)
            if claim.confidence_score is not None
            else None
        ),
        created_at=claim.created_at.isoformat(),
    )


@router.get(
    "/claims/{claim_id}/evidence",
    response_model=list[dict],
    summary="Get evidence linked to a claim",
)
async def get_claim_evidence(
    claim_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    repo = EvidenceRepository(session)
    import uuid

    links = await repo.get_claim_evidence(UUID(claim_id))
    return [
        {
            "evidence_chunk_id": str(link.evidence_chunk_id),
            "relationship": link.relationship_,
            "support_score": (
                float(link.support_score)
                if link.support_score is not None
                else None
            ),
            "contradiction_score": (
                float(link.contradiction_score)
                if link.contradiction_score is not None
                else None
            ),
        }
        for link in links
    ]


# ---------------------------------------------------------------------------
# Evidence ingestion (seed)
# ---------------------------------------------------------------------------


class EvidenceIngestRequest(BaseModel):
    source_type: str
    title: str
    publisher: str
    url: str | None = None
    document_type: str = "OTHER"
    document_title: str
    document_content: str


class EvidenceIngestResponse(BaseModel):
    source_id: str
    document_id: str
    checksum: str


@router.post(
    "/evidence/ingest",
    response_model=EvidenceIngestResponse,
    summary="Ingest an evidence document (idempotent by checksum)",
)
async def ingest_evidence(
    request: EvidenceIngestRequest,
    session: AsyncSession = Depends(get_session),
) -> EvidenceIngestResponse:
    ingestion = EvidenceIngestionService(session)

    # Create source.
    source = await ingestion.ingest_source(
        source_type=request.source_type,
        title=request.title,
        publisher=request.publisher,
        url=request.url,
    )

    # Ingest document (idempotent by checksum).
    document = await ingestion.ingest_document(
        source_id=str(source.id),
        document_type=request.document_type,
        title=request.document_title,
        content=request.document_content,
    )

    # Calculate checksum for response.
    import hashlib

    normalized = " ".join(request.document_content.strip().split()).lower()
    checksum = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    return EvidenceIngestResponse(
        source_id=str(source.id),
        document_id=str(document.id),
        checksum=checksum,
    )


__all__ = ["router"]
