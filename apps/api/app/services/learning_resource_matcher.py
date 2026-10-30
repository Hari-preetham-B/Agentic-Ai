"""Learning resource matching engine.

Deterministic ranking of learning resources against skill gaps.

Ranking uses observable signals:
- skill relevance (relevance_score from resource-skill mapping)
- coverage (whether the resource covers the needed skill)
- difficulty fit (resource difficulty vs current proficiency)
- prerequisite satisfaction
- career relevance
- estimated effort (lower effort preferred for same relevance)
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


class LearningResourceMatcher:
    """Deterministic learning resource matching and ranking."""

    # Difficulty fit scores: how well a resource difficulty matches a proficiency level.
    _DIFFICULTY_FIT: dict[tuple[str, str], float] = {
        ("BEGINNER", "BEGINNER"): 1.0,
        ("BEGINNER", "INTERMEDIATE"): 0.7,
        ("BEGINNER", "ADVANCED"): 0.4,
        ("BEGINNER", "EXPERT"): 0.2,
        ("INTERMEDIATE", "BEGINNER"): 0.8,
        ("INTERMEDIATE", "INTERMEDIATE"): 1.0,
        ("INTERMEDIATE", "ADVANCED"): 0.7,
        ("INTERMEDIATE", "EXPERT"): 0.4,
        ("ADVANCED", "BEGINNER"): 0.5,
        ("ADVANCED", "INTERMEDIATE"): 0.8,
        ("ADVANCED", "ADVANCED"): 1.0,
        ("ADVANCED", "EXPERT"): 0.7,
        ("EXPERT", "BEGINNER"): 0.3,
        ("EXPERT", "INTERMEDIATE"): 0.5,
        ("EXPERT", "ADVANCED"): 0.8,
        ("EXPERT", "EXPERT"): 1.0,
    }

    # Resource type weights.
    _TYPE_WEIGHTS: dict[str, float] = {
        "COURSE": 1.0,
        "TUTORIAL": 0.9,
        "DOCUMENTATION": 0.85,
        "BOOK": 0.8,
        "PROJECT": 0.95,
        "PRACTICE": 0.9,
        "VIDEO": 0.75,
    }

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def rank_resources(
        self,
        *,
        skill_name: str,
        current_proficiency: str | None,
        resources: list[dict[str, Any]],
        resource_skill_mappings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Rank learning resources for a given skill gap.

        Returns a list of resource dicts with an added 'match_score' field,
        sorted by match_score descending (ties broken alphabetically by title).
        """
        # Build a lookup of resource_id -> skill mapping info.
        mapping_lookup: dict[str, dict[str, Any]] = {}
        for m in resource_skill_mappings:
            if m.get("skill_name") == skill_name:
                mapping_lookup[m.get("resource_id")] = m

        scored: list[dict[str, Any]] = []
        for resource in resources:
            rid = resource.get("id")
            mapping = mapping_lookup.get(rid, {})

            # Skill relevance from mapping.
            relevance = mapping.get("relevance_score", 0.5)
            if relevance is None:
                relevance = 0.5

            # Coverage: does the resource cover this skill?
            coverage = 1.0 if mapping else 0.5

            # Difficulty fit.
            resource_diff = resource.get("difficulty")
            user_prof = current_proficiency or "BEGINNER"
            diff_fit = self._DIFFICULTY_FIT.get(
                (resource_diff or "INTERMEDIATE", user_prof), 0.5
            )

            # Type weight.
            rtype = resource.get("resource_type", "COURSE")
            type_weight = self._TYPE_WEIGHTS.get(rtype, 0.5)

            # Effort factor: lower effort preferred (inverse, capped).
            hours = resource.get("estimated_hours", 10.0) or 10.0
            effort_factor = 1.0 / (1.0 + hours / 20.0)

            # Composite score.
            score = (
                0.35 * relevance
                + 0.20 * coverage
                + 0.20 * diff_fit
                + 0.15 * type_weight
                + 0.10 * effort_factor
            )

            scored.append({
                **resource,
                "match_score": round(score, 4),
                "relevance_score": relevance,
                "coverage": coverage,
                "difficulty_fit": diff_fit,
            })

        # Sort by match_score descending, then title ascending for determinism.
        scored.sort(key=lambda r: (-r["match_score"], r.get("title", "")))
        return scored


__all__ = ["LearningResourceMatcher"]
