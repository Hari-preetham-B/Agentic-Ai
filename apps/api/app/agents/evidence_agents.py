"""Evidence Agent — real implementation for claim/evidence verification.

Orchestrates:

1. Claim extraction from generated text.
2. Evidence retrieval via semantic similarity.
3. Claim/evidence comparison and contradiction detection.
4. Deterministic confidence calculation.
5. Evidence-backed response formatting.

The LLM may assist with claim extraction, explanation, and summarization.
The LLM must NOT decide confidence, classification, or source reliability.
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.contracts import AgentResult, AgentState, AgentStatus
from app.core.embedding import FakeEmbeddingProvider
from app.core.llm import FakeLLMProvider, LLMProvider
from app.services.claim_verification_service import (
    ClaimVerificationService,
    VerifiedClaim,
)
from app.services.repositories import EvidenceRepository
from app.services.trace import TraceService
from sqlalchemy.ext.asyncio import AsyncSession


class EvidenceAgent:
    """Evidence Agent — verifies claims against stored evidence.

    Workflow:
    1. Request get_evidence tool if no evidence has been retrieved yet.
    2. Extract claims from input text.
    3. Retrieve relevant evidence for each claim.
    4. Verify claims deterministically.
    5. Produce typed evidence-backed output.
    """

    name = "evidence_agent"

    def __init__(
        self,
        session: AsyncSession | None = None,
        llm_provider: LLMProvider | None = None,
        embedding_provider=None,
        trace_service: TraceService | None = None,
    ) -> None:
        self.session = session
        self.llm_provider = llm_provider or FakeLLMProvider()
        self.embedding_provider = embedding_provider or FakeEmbeddingProvider()
        self.trace = trace_service
        self.repo = EvidenceRepository(session) if session else None

    # ------------------------------------------------------------------
    # Agent run entry point
    # ------------------------------------------------------------------

    async def run(self, state: AgentState) -> AgentResult:
        start = time.perf_counter()
        errors: list[dict[str, Any]] = []
        output: dict[str, Any] | None = None

        try:
            text = state.user_input or state.context.get("input_text", "")
            if not text:
                raise ValueError("No input text provided for evidence verification.")

            profile_id = state.profile_id or state.context.get("profile_id")

            # Step 1: Extract claims from the input text.
            verification_service = ClaimVerificationService(
                session=self.session,
                embedding_provider=self.embedding_provider,
                llm_provider=self.llm_provider,
            )

            verified_claims = await verification_service.verify_text(
                text=text,
                profile_id=profile_id,
                context=state.context.get("context"),
            )

            # Step 2: Build typed output.
            claim_outputs = [vc.model_dump() for vc in verified_claims]

            # Count by status.
            status_counts: dict[str, int] = {}
            for vc in verified_claims:
                status_counts[vc.status] = status_counts.get(vc.status, 0) + 1

            output = {
                "capability": "evidence_verification",
                "input_text": text,
                "claims": claim_outputs,
                "summary": {
                    "total_claims": len(verified_claims),
                    "status_counts": status_counts,
                },
                "methodology": (
                    "Deterministic claim verification: extract claims, retrieve "
                    "evidence via pgvector similarity, compare claim against "
                    "evidence, calculate confidence from observable signals "
                    "(source hierarchy, similarity, contradiction), classify "
                    "deterministically."
                ),
            }

            status = AgentStatus.COMPLETED

        except Exception as exc:  # noqa: BLE001 - surface as agent failure
            errors.append(
                {"agent": self.name, "code": "AGENT_ERROR", "message": str(exc)}
            )
            status = AgentStatus.FAILED

        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentResult(
            agent_name=self.name,
            status=status,
            output=output,
            metadata={"provider": self.llm_provider.provider_name},
            errors=errors,
            duration_ms=duration_ms,
        )


__all__ = ["EvidenceAgent"]
