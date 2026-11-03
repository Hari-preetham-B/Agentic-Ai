"""Claim verification service.

Orchestrates the claim verification pipeline:

    Generated Response
    → Claim Extraction
    → Evidence Retrieval
    → Claim/Evidence Comparison
    → Contradiction Detection
    → Classification
    → Confidence Engine

All scoring and classification is deterministic — the LLM may assist with
claim extraction and explanation but never decides the final classification
or confidence score.
"""

from __future__ import annotations

import re
from typing import Any

from app.core.embedding import FakeEmbeddingProvider, EmbeddingProvider
from app.core.llm import FakeLLMProvider, LLMProvider
from app.models.evidence import Claim, ClaimEvidence
from app.services.claim_extraction_service import (
    ClaimExtractionService,
    ExtractedClaim,
)
from app.services.confidence_engine import ConfidenceEngine
from app.services.evidence_ingestion_service import EvidenceIngestionService
from app.services.evidence_retriever import ChunkResult, EvidenceRetriever
from app.services.repositories import EvidenceRepository
from sqlalchemy.ext.asyncio import AsyncSession


class VerifiedClaim:
    """A claim with its verification result."""

    def __init__(
        self,
        *,
        claim: ExtractedClaim,
        status: str,
        confidence: float,
        evidence: list[dict[str, Any]],
        contradictions: list[dict[str, Any]],
        explanation: str,
        factors: dict[str, Any] | None = None,
    ) -> None:
        self.claim = claim.claim_text
        self.claim_type = claim.claim_type
        self.importance = claim.importance
        self.status = status
        self.confidence = confidence
        self.evidence = evidence
        self.contradictions = contradictions
        self.explanation = explanation
        self.factors = factors or {}

    def model_dump(self) -> dict[str, Any]:
        return {
            "claim": self.claim,
            "claim_type": self.claim_type,
            "importance": self.importance,
            "status": self.status,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "contradictions": self.contradictions,
            "explanation": self.explanation,
            "factors": self.factors,
        }


class ClaimVerificationService:
    """Service for verifying claims against retrieved evidence."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.session = session
        self.repo = EvidenceRepository(session)
        self.ingestion = EvidenceIngestionService(
            session, embedding_provider=embedding_provider
        )
        self.retriever = EvidenceRetriever(
            session, embedding_provider=embedding_provider
        )
        self.extractor = ClaimExtractionService(
            llm_provider=llm_provider or FakeLLMProvider()
        )
        self.confidence_engine = ConfidenceEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def verify_text(
        self,
        *,
        text: str,
        profile_id: str | None = None,
        context: str | None = None,
    ) -> list[VerifiedClaim]:
        """Verify all claims in a text against stored evidence.

        Pipeline:
        1. Extract claims from text.
        2. For each claim, retrieve relevant evidence.
        3. Compare claim against evidence.
        4. Calculate confidence and classify.
        5. Persist claim and evidence links.
        6. Return verified claims.
        """
        claims = await self.extractor.extract_claims(text=text, context=context)

        verified: list[VerifiedClaim] = []
        for claim in claims:
            result = await self._verify_single_claim(
                claim=claim, profile_id=profile_id
            )
            verified.append(result)

        return verified

    async def verify_single_claim_text(
        self,
        *,
        claim_text: str,
        claim_type: str = "other",
        importance: str = "SUPPORTING",
        profile_id: str | None = None,
        context: str | None = None,
    ) -> VerifiedClaim:
        """Verify a single claim text against stored evidence."""
        claim = ExtractedClaim(
            claim_text=claim_text,
            claim_type=claim_type,
            importance=importance,
            context=context,
        )
        return await self._verify_single_claim(
            claim=claim, profile_id=profile_id
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _verify_single_claim(
        self,
        claim: ExtractedClaim,
        profile_id: str | None = None,
    ) -> VerifiedClaim:
        """Verify a single claim end-to-end."""
        # Step 1: Retrieve relevant evidence for the claim.
        chunks = await self.retriever.search(
            query=claim.claim_text,
            top_k=5,
            min_similarity=0.0,
        )

        # Step 2: Compare claim against evidence chunks.
        support_scores: list[float | None] = [None] * len(chunks)
        contradiction_scores: list[float | None] = [None] * len(chunks)
        relationships: list[str] = []
        evidence_list: list[dict[str, Any]] = []
        contradictions_list: list[dict[str, Any]] = []

        # Simple heuristic comparison: check keyword overlap between claim
        # and evidence content. This is deterministic and explainable.
        claim_keywords = self._keywords(claim.claim_text)

        for i, chunk in enumerate(chunks):
            chunk_keywords = self._keywords(chunk.content)
            overlap = len(claim_keywords & chunk_keywords)
            total = len(claim_keywords | chunk_keywords)
            jaccard = overlap / total if total > 0 else 0.0

            # Keyword overlap (recall) is the primary signal for short claims,
            # as pgvector similarity can be unreliable for short text.
            keyword_overlap = overlap / len(claim_keywords) if claim_keywords else 0.0

            # Combine Jaccard similarity with retrieval similarity.
            similarity = 0.6 * keyword_overlap + 0.4 * chunk.similarity_score

            # Determine relationship based on similarity threshold.
            # Low similarity means insufficient evidence, NOT contradiction.
            # Only high similarity (≥ 0.50) indicates support.
            if similarity >= 0.50:
                relationship = "SUPPORTS"
                support_scores[i] = similarity
            else:
                # similarity < 0.50 means insufficient evidence match,
                # not contradiction. Check for explicit negation mismatch
                # between claim and evidence to detect true contradiction.
                if self._has_negation_mismatch(claim.claim_text, chunk.content):
                    relationship = "CONTRADICTS"
                    contradiction_scores[i] = similarity
                else:
                    relationship = "CONTEXTUAL"

            relationships.append(relationship)

            evidence_list.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "source_id": chunk.source_id,
                    "source_type": chunk.source_type,
                    "title": chunk.title,
                    "publisher": chunk.publisher,
                    "url": chunk.url,
                    "similarity_score": chunk.similarity_score,
                    "keyword_overlap": keyword_overlap,
                    "relationship": relationship,
                    "content_snippet": chunk.content[:200],
                }
            )

            if relationship == "CONTRADICTS":
                contradictions_list.append(
                    {
                        "chunk_id": chunk.chunk_id,
                        "title": chunk.title,
                        "publisher": chunk.publisher,
                        "similarity_score": chunk.similarity_score,
                        "content_snippet": chunk.content[:200],
                    }
                )

        # Step 3: Calculate deterministic confidence.
        evidence_chunk_dicts = [
            {
                "source_type": e["source_type"],
                "document_type": "OTHER",
                "similarity_score": e["similarity_score"],
            }
            for e in evidence_list
        ]

        support_scores_filtered = [s for s in support_scores if s is not None]
        contradiction_scores_filtered = [s for s in contradiction_scores if s is not None]

        confidence_result = self.confidence_engine.calculate(
            evidence_chunks=evidence_chunk_dicts,
            support_scores=support_scores_filtered,
            contradiction_scores=contradiction_scores_filtered,
            relationships=relationships,
            directly_supported=len(support_scores_filtered) > 0,
        )

        # Step 4: Build explanation.
        explanation = self._build_explanation(
            claim=claim,
            confidence_result=confidence_result,
            support_count=len(support_scores),
            contradiction_count=len(contradiction_scores),
        )

        # Step 5: Persist claim and evidence links.
        import uuid

        claim_record = Claim(
            profile_id=uuid.UUID(profile_id) if profile_id else None,
            claim_text=claim.claim_text,
            claim_type=claim.claim_type,
            status=confidence_result.classification,
            confidence_score=confidence_result.score,
        )
        claim_record = await self.repo.create_claim(claim_record)

        for i, chunk in enumerate(chunks):
            if i >= len(relationships):
                break
            link = ClaimEvidence(
                claim_id=claim_record.id,
                evidence_chunk_id=chunk.chunk_id and uuid.UUID(chunk.chunk_id),
                relationship_=relationships[i],
                support_score=(
                    support_scores[i] if relationships[i] == "SUPPORTS" else None
                ),
                contradiction_score=(
                    contradiction_scores[i]
                    if relationships[i] == "CONTRADICTS"
                    else None
                ),
                metadata_={"claim_type": claim.claim_type},
            )
            await self.repo.link_claim_evidence(link)

        return VerifiedClaim(
            claim=claim,
            status=confidence_result.classification,
            confidence=confidence_result.score,
            evidence=evidence_list,
            contradictions=contradictions_list,
            explanation=explanation,
            factors={
                "base_score": confidence_result.factors.base_score,
                "agreement_score": confidence_result.factors.agreement_score,
                "contradiction_penalty": confidence_result.factors.contradiction_penalty,
                "source_count": confidence_result.factors.source_count,
                "support_count": confidence_result.factors.support_count,
                "contradiction_count": confidence_result.factors.contradiction_count,
            },
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _keywords(text: str) -> set[str]:
        """Extract lowercase alphanumeric keywords from text."""
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]*\b", text.lower())
        stopwords = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
            "for", "of", "with", "by", "from", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "will", "would", "could", "should", "may", "might", "can",
            "this", "that", "these", "those", "i", "you", "he", "she", "it",
            "we", "they", "what", "which", "who", "when", "where", "why",
            "how", "all", "each", "every", "some", "any", "no", "not",
        }
        return {w for w in words if w not in stopwords and len(w) > 2}

    @staticmethod
    def _has_negation_mismatch(claim_text: str, evidence_text: str) -> bool:
        """Detect explicit negation mismatch between claim and evidence.

        Returns True when the claim contains a negation word that the
        evidence does not (or vice versa), indicating potential logical
        opposition rather than mere low similarity.

        Examples of negation triggers: not, never, no, exclusively, only,
        doesn't, isn't, cannot, won't, shouldn't, mustn't.
        """
        negation_triggers = {
            "not", "never", "no", "exclusively", "only",
            "doesn't", "does not", "isn't", "is not",
            "can't", "cannot", "won't", "will not",
            "shouldn't", "should not", "mustn't", "must not",
        }

        claim_lower = claim_text.lower()
        evidence_lower = evidence_text.lower()

        claim_has_negation = any(
            trigger in claim_lower for trigger in negation_triggers
        )
        evidence_has_negation = any(
            trigger in evidence_lower for trigger in negation_triggers
        )

        # Negation mismatch: claim negates what evidence affirms (or vice versa)
        return claim_has_negation != evidence_has_negation

    @staticmethod
    def _build_explanation(
        *,
        claim: ExtractedClaim,
        confidence_result: Any,
        support_count: int,
        contradiction_count: int,
    ) -> str:
        """Build a human-readable explanation of the verification result."""
        status = confidence_result.classification
        score = confidence_result.score

        if status == "SUPPORTED":
            return (
                f"Claim '{claim.claim_text}' is SUPPORTED with {score:.0%} "
                f"confidence based on {support_count} supporting evidence "
                f"source(s) with no material contradiction."
            )
        if status == "INFERRED":
            return (
                f"Claim '{claim.claim_text}' is INFERRED with {score:.0%} "
                f"confidence — reasonable inference from available evidence "
                f"but not directly stated."
            )
        if status == "UNCERTAIN":
            return (
                f"Claim '{claim.claim_text}' is UNCERTAIN with {score:.0%} "
                f"confidence — insufficient or weak evidence to verify."
            )
        # CONTRADICTED
        return (
            f"Claim '{claim.claim_text}' is CONTRADICTED — reliable evidence "
            f"materially conflicts with this claim."
        )


__all__ = ["ClaimVerificationService", "VerifiedClaim"]
