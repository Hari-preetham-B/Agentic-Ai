"""Evidence tools for agent execution.

Tools for evidence intelligence operations. They use the service/repository
layer — never raw SQL or direct SQLAlchemy session manipulation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.claim_verification_service import ClaimVerificationService
from app.services.evidence_ingestion_service import EvidenceIngestionService
from app.services.evidence_retriever import EvidenceRetriever
from app.services.repositories import EvidenceRepository
from app.tools import Tool


# ---------------------------------------------------------------------------
# get_evidence tool
# ---------------------------------------------------------------------------


class GetEvidenceInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    chunk_id: str = Field(..., description="Evidence chunk ID.")


class GetEvidenceOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class GetEvidenceTool(Tool[GetEvidenceInput, GetEvidenceOutput]):
    input_schema = GetEvidenceInput
    output_schema = GetEvidenceOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_evidence",
            description="Retrieve an evidence chunk by ID with full provenance.",
        )
        self._session = session

    async def _run(self, input_data: GetEvidenceInput) -> dict[str, Any]:
        retriever = EvidenceRetriever(self._session)
        result = await retriever.get_chunk(input_data.chunk_id)
        if result is None:
            raise ValueError(f"Evidence chunk not found: {input_data.chunk_id}")
        return result.model_dump()


# ---------------------------------------------------------------------------
# search_evidence tool
# ---------------------------------------------------------------------------


class SearchEvidenceInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: str = Field(..., description="Search query text.")
    top_k: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)
    source_type: str | None = Field(default=None)


class SearchEvidenceOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    results: list[dict] = Field(default_factory=list)


class SearchEvidenceTool(Tool[SearchEvidenceInput, SearchEvidenceOutput]):
    input_schema = SearchEvidenceInput
    output_schema = SearchEvidenceOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="search_evidence",
            description="Search evidence chunks by semantic similarity.",
        )
        self._session = session

    async def _run(self, input_data: SearchEvidenceInput) -> dict[str, Any]:
        retriever = EvidenceRetriever(self._session)
        results = await retriever.search(
            query=input_data.query,
            top_k=input_data.top_k,
            min_similarity=input_data.min_similarity,
            source_type=input_data.source_type,
        )
        return {"results": [r.model_dump() for r in results]}


# ---------------------------------------------------------------------------
# verify_claim tool
# ---------------------------------------------------------------------------


class VerifyClaimInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_text: str = Field(..., description="The claim text to verify.")
    claim_type: str = Field(default="other")
    importance: str = Field(default="SUPPORTING")
    profile_id: str | None = Field(default=None)
    context: str | None = Field(default=None)


class VerifyClaimOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim: str
    claim_type: str
    importance: str
    status: str
    confidence: float
    evidence: list[dict] = Field(default_factory=list)
    contradictions: list[dict] = Field(default_factory=list)
    explanation: str
    factors: dict[str, Any] = Field(default_factory=dict)


class VerifyClaimTool(Tool[VerifyClaimInput, VerifyClaimOutput]):
    input_schema = VerifyClaimInput
    output_schema = VerifyClaimOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="verify_claim",
            description="Verify a claim against stored evidence deterministically.",
        )
        self._session = session

    async def _run(self, input_data: VerifyClaimInput) -> dict[str, Any]:
        service = ClaimVerificationService(self._session)
        result = await service.verify_single_claim_text(
            claim_text=input_data.claim_text,
            claim_type=input_data.claim_type,
            importance=input_data.importance,
            profile_id=input_data.profile_id,
            context=input_data.context,
        )
        return result.model_dump()


# ---------------------------------------------------------------------------
# get_claim_evidence tool
# ---------------------------------------------------------------------------


class GetClaimEvidenceInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str = Field(..., description="Claim ID.")


class GetClaimEvidenceOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    claim_id: str
    evidence_links: list[dict] = Field(default_factory=list)


class GetClaimEvidenceTool(Tool[GetClaimEvidenceInput, GetClaimEvidenceOutput]):
    input_schema = GetClaimEvidenceInput
    output_schema = GetClaimEvidenceOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_claim_evidence",
            description="Retrieve evidence linked to a claim.",
        )
        self._session = session

    async def _run(self, input_data: GetClaimEvidenceInput) -> dict[str, Any]:
        repo = EvidenceRepository(self._session)
        links = await repo.get_claim_evidence(UUID(input_data.claim_id))
        return {
            "claim_id": input_data.claim_id,
            "evidence_links": [
                {
                    "evidence_chunk_id": str(link.evidence_chunk_id),
                    "relationship": link.relationship,
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
            ],
        }


__all__ = [
    "GetEvidenceInput",
    "GetEvidenceOutput",
    "GetEvidenceTool",
    "SearchEvidenceInput",
    "SearchEvidenceOutput",
    "SearchEvidenceTool",
    "VerifyClaimInput",
    "VerifyClaimOutput",
    "VerifyClaimTool",
    "GetClaimEvidenceInput",
    "GetClaimEvidenceOutput",
    "GetClaimEvidenceTool",
    "build_get_evidence_tool",
    "build_search_evidence_tool",
    "build_verify_claim_tool",
    "build_get_claim_evidence_tool",
]


def build_get_evidence_tool(session: AsyncSession) -> GetEvidenceTool:
    return GetEvidenceTool(session)


def build_search_evidence_tool(session: AsyncSession) -> SearchEvidenceTool:
    return SearchEvidenceTool(session)


def build_verify_claim_tool(session: AsyncSession) -> VerifyClaimTool:
    return VerifyClaimTool(session)


def build_get_claim_evidence_tool(session: AsyncSession) -> GetClaimEvidenceTool:
    return GetClaimEvidenceTool(session)
