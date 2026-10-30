"""Claim extraction service.

Extracts typed claims from generated text. Can use the LLM provider for
extraction but provides a deterministic fallback for tests.

Each claim contains:
- claim_text
- claim_type
- importance
- source/context if available
"""

from __future__ import annotations

import re
from typing import Any

from app.core.llm import FakeLLMProvider, LLMProvider
from pydantic import BaseModel, ConfigDict, Field


class ExtractedClaim(BaseModel):
    """A single claim extracted from generated text."""

    model_config = ConfigDict(frozen=True)

    claim_text: str = Field(..., description="The claim statement.")
    claim_type: str = Field(
        ..., description="Type of claim (e.g. skill_requirement, education, tool)."
    )
    importance: str = Field(
        default="SUPPORTING",
        description="Importance level: CORE, IMPORTANT, SUPPORTING.",
    )
    context: str | None = Field(
        default=None, description="Source context where the claim appeared."
    )


class ClaimExtractionService:
    """Service for extracting claims from generated text."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.llm_provider = llm_provider or FakeLLMProvider()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def extract_claims(
        self,
        *,
        text: str,
        context: str | None = None,
    ) -> list[ExtractedClaim]:
        """Extract claims from generated text.

        Attempts LLM-based extraction first. Falls back to deterministic
        sentence-based extraction if the LLM is unavailable or returns
        unusable output.
        """
        # Try LLM-based extraction.
        try:
            claims = await self._extract_with_llm(text, context)
            if claims:
                return claims
        except Exception:
            pass

        # Deterministic fallback: split text into sentences and treat each
        # meaningful sentence as a claim.
        return self._extract_deterministic(text, context)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _extract_with_llm(
        self,
        text: str,
        context: str | None = None,
    ) -> list[ExtractedClaim]:
        """Use the LLM provider to extract claims."""
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract factual claims from the following text. "
                    "Return each claim as a JSON object with keys: "
                    "claim_text, claim_type, importance. "
                    "claim_type should be one of: skill_requirement, "
                    "education, tool, experience, certification, other. "
                    "importance should be one of: CORE, IMPORTANT, "
                    "SUPPORTING. Return a JSON array of claim objects."
                ),
            },
            {
                "role": "user",
                "content": f"Text: {text}",
            },
        ]

        response = await self.llm_provider.generate(messages)
        if not response.content:
            return []

        # Parse the LLM response as JSON.
        import json

        try:
            data = json.loads(response.content)
        except (json.JSONDecodeError, ValueError):
            # Try to find a JSON array in the response.
            match = re.search(r"\[.*\]", response.content, re.DOTALL)
            if not match:
                return []
            try:
                data = json.loads(match.group(0))
            except (json.JSONDecodeError, ValueError):
                return []

        claims: list[ExtractedClaim] = []
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                claim_text = item.get("claim_text", "").strip()
                if not claim_text:
                    continue
                claims.append(
                    ExtractedClaim(
                        claim_text=claim_text,
                        claim_type=item.get("claim_type", "other"),
                        importance=item.get("importance", "SUPPORTING"),
                        context=context,
                    )
                )
        return claims

    @staticmethod
    def _extract_deterministic(
        text: str,
        context: str | None = None,
    ) -> list[ExtractedClaim]:
        """Deterministically split text into sentence-level claims."""
        # Split on sentence-ending punctuation followed by whitespace.
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        claims: list[ExtractedClaim] = []
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 5:
                continue
            # Classify claim type heuristically.
            claim_type = "other"
            lower = sentence.lower()
            if any(
                w in lower
                for w in ["skill", "python", "java", "sql", "aws", "docker"]
            ):
                claim_type = "skill_requirement"
            elif any(w in lower for w in ["degree", "bachelor", "master", "phd"]):
                claim_type = "education"
            elif any(w in lower for w in ["tool", "software", "platform"]):
                claim_type = "tool"

            claims.append(
                ExtractedClaim(
                    claim_text=sentence,
                    claim_type=claim_type,
                    importance="SUPPORTING",
                    context=context,
                )
            )
        return claims


__all__ = ["ClaimExtractionService", "ExtractedClaim"]
