"""Roadmap sequencing engine.

Deterministic prerequisite-aware ordering of roadmap skills.

Uses topological sorting to ensure prerequisites appear before dependents.
Already-satisfied skills are omitted. Partial skills may appear as
reinforcement tasks.

Ties are broken deterministically (alphabetically by skill name).
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class RoadmapSequenceEngine:
    """Deterministic prerequisite-aware roadmap sequencing."""

    def sequence(
        self,
        *,
        skills_to_learn: list[str],
        graph: dict[str, list[str]],
        known_skills: set[str],
        priority_map: dict[str, str],
    ) -> list[str]:
        """Produce a deterministic ordered list of skills to learn.

        Args:
            skills_to_learn: Skills that need to be learned.
            graph: Dependency graph (skill -> list of prerequisites).
            known_skills: Set of skills the user already has.
            priority_map: Priority (P0/P1/P2) for each skill.

        Returns:
            Ordered list of skill names (prerequisites first).
        """
        # Filter out already-satisfied skills (all prerequisites met and
        # skill itself is known).
        filtered = []
        for skill in skills_to_learn:
            if skill in known_skills:
                continue
            # Check if all direct prerequisites are satisfied.
            prereqs = graph.get(skill, [])
            # Only include if at least one prerequisite is missing or the
            # skill itself is not known.
            filtered.append(skill)

        if not filtered:
            return []

        # Build subgraph for filtered skills + their unsatisfied prerequisites.
        all_needed: set[str] = set(filtered)
        for skill in filtered:
            prereqs = graph.get(skill, [])
            for prereq in prereqs:
                if prereq not in known_skills:
                    all_needed.add(prereq)

        # Build adjacency for topological sort.
        in_degree: dict[str, int] = {s: 0 for s in all_needed}
        dependents: dict[str, list[str]] = defaultdict(list)

        for skill in all_needed:
            prereqs = graph.get(skill, [])
            for prereq in prereqs:
                if prereq in all_needed:
                    in_degree[skill] += 1
                    dependents[prereq].append(skill)

        # Kahn's algorithm with priority + alphabetical tie-breaking.
        # Priority order: P0 > P1 > P2 (lower number = higher priority).
        priority_rank = {"P0": 0, "P1": 1, "P2": 2}

        def sort_key(skill: str) -> tuple[int, int, str]:
            p = priority_rank.get(priority_map.get(skill, "P2"), 2)
            return (p, 0, skill)

        queue = sorted(
            [s for s in all_needed if in_degree[s] == 0],
            key=lambda s: (priority_rank.get(priority_map.get(s, "P2"), 2), s),
        )
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            for dependent in sorted(dependents.get(node, [])):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    queue.sort(
                        key=lambda s: (
                            priority_rank.get(priority_map.get(s, "P2"), 2),
                            s,
                        )
                    )

        return result

    def get_missing_prerequisites(
        self,
        skill: str,
        graph: dict[str, list[str]],
        known_skills: set[str],
    ) -> list[str]:
        """Return prerequisites for a skill that are not in known_skills."""
        prereqs = graph.get(skill, [])
        return [p for p in prereqs if p not in known_skills]

    def get_unlocked_skills(
        self,
        skill: str,
        graph: dict[str, list[str]],
    ) -> list[str]:
        """Return skills that directly depend on this skill."""
        dependents = []
        for node, prereqs in graph.items():
            if skill in prereqs:
                dependents.append(node)
        return sorted(dependents)


__all__ = ["RoadmapSequenceEngine"]
