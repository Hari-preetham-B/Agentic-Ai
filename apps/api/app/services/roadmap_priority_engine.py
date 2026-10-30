"""Roadmap priority engine.

Deterministic priority calculation for learning roadmap items.

Priority combines:
- skill-gap severity
- career importance (CORE/IMPORTANT/SUPPORTING)
- dependency centrality (how many downstream skills this unlocks)
- prerequisite importance
- current proficiency
- estimated learning effort

Output: P0 (critical), P1 (important), P2 (supporting)
"""

from __future__ import annotations

from typing import Any


class RoadmapPriorityEngine:
    """Deterministic roadmap priority calculation."""

    # Importance weights for career skill importance.
    _IMPORTANCE_WEIGHTS: dict[str, float] = {
        "CORE": 1.0,
        "IMPORTANT": 0.7,
        "SUPPORTING": 0.4,
    }

    # Proficiency weights (lower proficiency = higher priority).
    _PROFICIENCY_WEIGHTS: dict[str, float] = {
        "BEGINNER": 1.0,
        "INTERMEDIATE": 0.6,
        "ADVANCED": 0.3,
        "EXPERT": 0.1,
    }

    # Priority thresholds.
    _P0_THRESHOLD = 0.70
    _P1_THRESHOLD = 0.40

    def calculate_priority(
        self,
        *,
        skill_name: str,
        importance: str,
        current_proficiency: str | None,
        gap_severity: float,
        downstream_count: int,
        total_skills: int,
        estimated_hours: float | None = None,
    ) -> str:
        """Calculate deterministic priority for a skill.

        Args:
            skill_name: The skill name.
            importance: Career skill importance (CORE/IMPORTANT/SUPPORTING).
            current_proficiency: User's current proficiency level.
            gap_severity: How severe the gap is (0.0 to 1.0).
            downstream_count: Number of downstream skills this skill unlocks.
            total_skills: Total number of skills in the gap.
            estimated_hours: Estimated hours to learn.

        Returns:
            "P0", "P1", or "P2".
        """
        importance_weight = self._IMPORTANCE_WEIGHTS.get(
            importance.upper(), 0.4
        )
        prof_weight = self._PROFICIENCY_WEIGHTS.get(
            (current_proficiency or "BEGINNER").upper(), 1.0
        )

        # Dependency centrality: normalized downstream count.
        centrality = (
            downstream_count / max(total_skills - 1, 1)
            if total_skills > 1
            else 0.0
        )

        # Effort factor: lower effort = slightly higher priority.
        hours = estimated_hours or 10.0
        effort_factor = 1.0 / (1.0 + hours / 20.0)

        # Composite priority score.
        score = (
            0.35 * gap_severity
            + 0.25 * importance_weight
            + 0.20 * prof_weight
            + 0.15 * centrality
            + 0.05 * effort_factor
        )

        if score >= self._P0_THRESHOLD:
            return "P0"
        if score >= self._P1_THRESHOLD:
            return "P1"
        return "P2"

    def calculate_downstream_count(
        self,
        skill: str,
        graph: dict[str, list[str]],
    ) -> int:
        """Count how many skills depend on this skill (directly or transitively).

        A skill that unlocks many downstream skills has higher centrality.
        """
        # Build reverse graph: prerequisite -> list of dependents
        dependents: dict[str, set[str]] = {}
        for node, prereqs in graph.items():
            for prereq in prereqs:
                dependents.setdefault(prereq, set()).add(node)

        # Count all transitive dependents.
        visited: set[str] = set()
        stack = [skill]
        while stack:
            current = stack.pop()
            for dep in dependents.get(current, set()):
                if dep not in visited:
                    visited.add(dep)
                    stack.append(dep)
        return len(visited)


__all__ = ["RoadmapPriorityEngine"]
