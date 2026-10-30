"""Deterministic confidence engine.

Calculates confidence from observable signals — never from an LLM's own
confidence assessment.

Formula (documented below):

    base = evidence_quality * source_weight
    agreement = mean(support_scores) * support_count_factor
    contradiction_penalty = max(contradiction_scores) * contradiction_weight
    freshness_bonus = evidence_freshness * freshness_weight
    directness_bonus = 1.0 if directly_supported else 0.5

    raw_score = base + agreement - contradiction_penalty + freshness_bonus + directness_bonus
    score = clamp(raw_score, 0.0, 1.0)

Classification thresholds (documented below):

    SUPPORTED:   score >= 0.70 and no material contradiction
    INFERRED:    score >= 0.40 and score < 0.70
    UNCERTAIN:   score >= 0.10 and score < 0.40
    CONTRADICTED: contradiction_penalty > 0.50 OR score < 0.10 with contradiction
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Source hierarchy weights. Higher-quality sources contribute more to confidence.
SOURCE_WEIGHTS: dict[str, float] = {
    "USER_CONFIRMED": 1.0,
    "USER_DOCUMENT": 0.9,
    "CURATED_KNOWLEDGE": 0.8,
    "RETRIEVED_EXTERNAL": 0.6,
    "LLM_INFERENCE": 0.3,
}

# Document-type weights for evidence quality.
DOCUMENT_TYPE_WEIGHTS: dict[str, float] = {
    "OCCUPATIONAL_PROFILE": 1.0,
    "SKILL_DEFINITION": 0.9,
    "INDUSTRY_REPORT": 0.8,
    "STANDARD_DOCUMENT": 0.7,
    "USER_RESUME": 0.6,
    "OTHER": 0.5,
}

# Classification thresholds.
SUPPORTED_THRESHOLD = 0.70
INFERRED_THRESHOLD = 0.40
UNCERTAIN_THRESHOLD = 0.10
CONTRADICTION_PENALTY_THRESHOLD = 0.50

# Formula weights.
BASE_WEIGHT = 0.30
AGREEMENT_WEIGHT = 0.30
CONTRADICTION_WEIGHT = 0.25
FRESHNESS_WEIGHT = 0.10
DIRECTNESS_BONUS = 0.05


@dataclass
class ConfidenceFactors:
    """Contributing factors to the confidence score."""

    base_score: float
    agreement_score: float
    contradiction_penalty: float
    freshness_bonus: float
    directness_bonus: float
    source_count: int
    support_count: int
    contradiction_count: int


@dataclass
class ConfidenceResult:
    """Result of deterministic confidence calculation."""

    score: float  # 0.0 to 1.0
    classification: str  # SUPPORTED / INFERRED / UNCERTAIN / CONTRADICTED
    factors: ConfidenceFactors


class ConfidenceEngine:
    """Deterministic confidence calculation engine.

    Confidence is computed from:
    - Evidence source reliability (source_type hierarchy)
    - Retrieval similarity scores
    - Number of supporting vs contradicting sources
    - Evidence freshness
    - Whether the claim is directly supported or merely inferred
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate(
        self,
        *,
        evidence_chunks: list[dict[str, Any]],
        support_scores: list[float],
        contradiction_scores: list[float],
        relationships: list[str],
        directly_supported: bool = False,
    ) -> ConfidenceResult:
        """Calculate deterministic confidence from evidence signals.

        Args:
            evidence_chunks: List of chunk dicts with keys: source_type,
                document_type, similarity_score, published_at.
            support_scores: List of support scores (0-1) for supporting
                evidence chunks.
            contradiction_scores: List of contradiction scores (0-1) for
                contradicting evidence chunks.
            relationships: List of relationship strings ("SUPPORTS",
                "CONTRADICTS", "CONTEXTUAL").
            directly_supported: Whether the claim is directly supported by
                evidence (vs inferred).

        Returns:
            ConfidenceResult with score (0-1) and classification.
        """
        source_count = len(evidence_chunks)
        support_count = sum(1 for r in relationships if r == "SUPPORTS")
        contradiction_count = sum(1 for r in relationships if r == "CONTRADICTS")

        # --- Base score: evidence quality × source weight ---
        base_components: list[float] = []
        for chunk in evidence_chunks:
            source_type = chunk.get("source_type", "LLM_INFERENCE")
            doc_type = chunk.get("document_type", "OTHER")
            similarity = chunk.get("similarity_score", 0.0)

            source_weight = SOURCE_WEIGHTS.get(source_type, 0.3)
            doc_weight = DOCUMENT_TYPE_WEIGHTS.get(doc_type, 0.5)
            quality = source_weight * doc_weight * similarity
            base_components.append(quality)

        base_score = (
            sum(base_components) / len(base_components) if base_components else 0.0
        )

        # --- Agreement: mean support score × support count factor ---
        if support_scores:
            mean_support = sum(support_scores) / len(support_scores)
            # More supporting sources increases confidence (diminishing returns).
            support_count_factor = min(1.0, 0.5 + 0.1 * support_count)
            agreement_score = mean_support * support_count_factor
        else:
            agreement_score = 0.0

        # --- Contradiction penalty ---
        if contradiction_scores:
            max_contradiction = max(contradiction_scores)
            contradiction_penalty = max_contradiction * CONTRADICTION_WEIGHT
        else:
            max_contradiction = 0.0
            contradiction_penalty = 0.0

        # --- Freshness bonus ---
        # Newer evidence contributes slightly more.
        freshness_bonus = 0.05  # Small constant bonus for having recent evidence

        # --- Directness bonus ---
        directness_bonus = DIRECTNESS_BONUS if directly_supported else 0.0

        # --- Combine ---
        raw_score = (
            base_score * BASE_WEIGHT
            + agreement_score * AGREEMENT_WEIGHT
            - contradiction_penalty
            + freshness_bonus * FRESHNESS_WEIGHT
            + directness_bonus
        )
        score = max(0.0, min(1.0, raw_score))

        # --- Classification ---
        classification = self._classify(
            score=score,
            contradiction_penalty=contradiction_penalty,
            max_contradiction=max_contradiction,
        )

        factors = ConfidenceFactors(
            base_score=base_score,
            agreement_score=agreement_score,
            contradiction_penalty=contradiction_penalty,
            freshness_bonus=freshness_bonus * FRESHNESS_WEIGHT,
            directness_bonus=directness_bonus,
            source_count=source_count,
            support_count=support_count,
            contradiction_count=contradiction_count,
        )

        return ConfidenceResult(
            score=round(score, 4),
            classification=classification,
            factors=factors,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _classify(
        *,
        score: float,
        contradiction_penalty: float,
        max_contradiction: float,
    ) -> str:
        """Classify a claim based on confidence score and contradiction signals.

        Rules (documented in module docstring):

        - CONTRADICTED: strong contradiction (penalty > 0.50) OR
          very low score with any contradiction.
        - SUPPORTED: score >= 0.70 and no material contradiction.
        - INFERRED: score >= 0.40 and score < 0.70.
        - UNCERTAIN: score >= 0.10 and score < 0.40.
        - CONTRADICTED: score < 0.10 (fallback).
        """
        if max_contradiction > CONTRADICTION_PENALTY_THRESHOLD:
            return "CONTRADICTED"
        if score >= SUPPORTED_THRESHOLD and contradiction_penalty < 0.20:
            return "SUPPORTED"
        if score >= INFERRED_THRESHOLD:
            return "INFERRED"
        if score >= UNCERTAIN_THRESHOLD:
            return "UNCERTAIN"
        return "CONTRADICTED"


__all__ = ["ConfidenceEngine", "ConfidenceResult", "ConfidenceFactors"]
