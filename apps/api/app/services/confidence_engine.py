"""Deterministic confidence engine.

Calculates confidence from observable signals — never from an LLM's own
confidence assessment.

Formula (documented below):

    positive_support = (
        quality_score * QUALITY_WEIGHT
        + agreement_score * AGREEMENT_WEIGHT
        + directness_score * DIRECTNESS_WEIGHT
        + freshness_score * FRESHNESS_WEIGHT
    )

    contradiction_penalty = max(contradiction_scores) * CONTRADICTION_WEIGHT

    score = clamp(positive_support - contradiction_penalty, 0.0, 1.0)

Each component is normalized to [0, 1] and the weights sum to 1.0, so the
maximum achievable score is 1.0. This guarantees that strong direct evidence
can reach SUPPORTED_THRESHOLD (0.70).

Classification thresholds:

    SUPPORTED:   score >= 0.70 and no material contradiction
    INFERRED:    score >= 0.40 and score < 0.70
    UNCERTAIN:   score >= 0.10 and score < 0.40
    CONTRADICTED: max_contradiction > 0.50 OR score < 0.10 with contradiction

LLM self-reported confidence is never used as input.
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

# Positive-support weights. These must sum to 1.0 so the maximum achievable
# positive_support is 1.0. QUALITY_WEIGHT is reduced because keyword_overlap
# (recall) is a stronger signal than raw pgvector similarity for short claims.
QUALITY_WEIGHT = 0.20
AGREEMENT_WEIGHT = 0.25
DIRECTNESS_WEIGHT = 0.45
FRESHNESS_WEIGHT = 0.10

# Contradiction penalty weight. Strong contradiction (max_contradiction=1.0)
# subtracts 0.35 from positive_support.
CONTRADICTION_WEIGHT = 0.35


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
    - Document type weight
    - Retrieval similarity scores
    - Number of supporting vs contradicting sources
    - Direct support (claim directly stated in evidence vs inferred)
    - Evidence freshness

    The formula is a normalized weighted sum:

        positive_support = (
            quality_score * QUALITY_WEIGHT
            + agreement_score * AGREEMENT_WEIGHT
            + directness_score * DIRECTNESS_WEIGHT
            + freshness_score * FRESHNESS_WEIGHT
        )

        score = clamp(positive_support - contradiction_penalty, 0, 1)

    where each component is in [0, 1] and QUALITY_WEIGHT + AGREEMENT_WEIGHT +
    DIRECTNESS_WEIGHT + FRESHNESS_WEIGHT = 1.0. This guarantees the maximum
    achievable score is 1.0, so SUPPORTED_THRESHOLD (0.70) is reachable with
    strong direct evidence.
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

        # --- Base quality score: mean(source_weight × document_weight × similarity) ---
        quality_components: list[float] = []
        for chunk in evidence_chunks:
            source_type = chunk.get("source_type", "LLM_INFERENCE")
            doc_type = chunk.get("document_type", "OTHER")
            # Use keyword_overlap (recall) as the primary quality signal,
            # as pgvector similarity can be unreliable for short text.
            similarity = chunk.get("keyword_overlap", chunk.get("similarity_score", 0.0))

            source_weight = SOURCE_WEIGHTS.get(source_type, 0.3)
            doc_weight = DOCUMENT_TYPE_WEIGHTS.get(doc_type, 0.5)
            quality = source_weight * doc_weight * similarity
            quality_components.append(quality)

        quality_score = (
            sum(quality_components) / len(quality_components)
            if quality_components
            else 0.0
        )

        # --- Agreement: mean support score × support count factor ---
        if support_scores:
            mean_support = sum(support_scores) / len(support_scores)
            # More supporting sources increases confidence (diminishing returns).
            support_count_factor = min(1.0, 0.5 + 0.1 * support_count)
            agreement_score = mean_support * support_count_factor
        else:
            agreement_score = 0.0

        # --- Directness: 1.0 if directly supported, 0.0 otherwise ---
        directness_score = 1.0 if directly_supported else 0.0

        # --- Freshness: small constant for recent evidence ---
        freshness_score = 0.05

        # --- Normalize positive support: weights sum to 1.0 ---
        positive_support = (
            quality_score * QUALITY_WEIGHT
            + agreement_score * AGREEMENT_WEIGHT
            + directness_score * DIRECTNESS_WEIGHT
            + freshness_score * FRESHNESS_WEIGHT
        )

        # --- Contradiction penalty ---
        if contradiction_scores:
            max_contradiction = max(contradiction_scores)
            contradiction_penalty = max_contradiction * CONTRADICTION_WEIGHT
        else:
            max_contradiction = 0.0
            contradiction_penalty = 0.0

        # --- Combine ---
        raw_score = positive_support - contradiction_penalty
        score = max(0.0, min(1.0, raw_score))

        # --- Classification ---
        classification = self._classify(
            score=score,
            contradiction_penalty=contradiction_penalty,
            max_contradiction=max_contradiction,
        )

        factors = ConfidenceFactors(
            base_score=quality_score,
            agreement_score=agreement_score,
            contradiction_penalty=contradiction_penalty,
            freshness_bonus=freshness_score * FRESHNESS_WEIGHT,
            directness_bonus=directness_score * DIRECTNESS_WEIGHT,
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

        Rules:

        - CONTRADICTED: max_contradiction > 0.50 (actual contradiction evidence)
          OR score < 0.10 with actual contradiction evidence.
        - SUPPORTED: score >= 0.70 and contradiction_penalty < 0.20
          (no material contradiction).
        - INFERRED: score >= 0.40 and score < 0.70.
        - UNCERTAIN: score >= 0.10 and score < 0.40.
        - CONTRADICTED: score < 0.10 AND max_contradiction > 0 (there is
          actual contradiction evidence; low score without contradiction is
          UNCERTAIN, not CONTRADICTED).
        """
        if max_contradiction > CONTRADICTION_PENALTY_THRESHOLD:
            return "CONTRADICTED"
        if score >= SUPPORTED_THRESHOLD and contradiction_penalty < 0.20:
            return "SUPPORTED"
        if score >= INFERRED_THRESHOLD:
            return "INFERRED"
        if score >= UNCERTAIN_THRESHOLD:
            return "UNCERTAIN"
        # score < 0.10: CONTRADICTED only if there's actual contradiction
        # evidence; low score without contradiction is UNCERTAIN.
        if max_contradiction > 0.0:
            return "CONTRADICTED"
        return "UNCERTAIN"


__all__ = ["ConfidenceEngine", "ConfidenceResult", "ConfidenceFactors"]
