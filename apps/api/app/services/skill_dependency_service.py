"""Skill dependency graph service.

Provides deterministic dependency graph operations: loading, validation,
cycle detection, prerequisite resolution, and prerequisite closure.

Uses curated dependency data — no LLM involvement.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning import SkillDependency
from app.services.repositories import ProfileRepository
from sqlalchemy import select


class SkillDependencyService:
    """Service for managing skill dependency graphs deterministically."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_dependencies(
        self, skill_name: str
    ) -> list[dict[str, Any]]:
        """Return all direct prerequisite dependencies for a skill."""
        # Find the skill in the skills table
        from app.models.profile import Skill

        # We need to find skill_id by name - but skills are profile-specific.
        # For dependency graph, we use skill_name as the key.
        # Dependencies are stored by skill_id, so we need a different approach.
        # Let's store dependencies by skill_name instead.

        # Actually, the model uses skill_id (UUID) referencing skills.id.
        # But skills are per-profile. For a global dependency graph, we need
        # a different approach. Let me use a name-based approach.

        # For simplicity, let's query all skill_dependencies and map by name.
        result = await self.session.execute(select(SkillDependency))
        deps = result.scalars().all()

        # We need to map skill_id -> skill_name. Let's build a lookup.
        skill_lookup = {}
        skill_result = await self.session.execute(select(Skill))
        for s in skill_result.scalars().all():
            skill_lookup[str(s.id)] = s.name

        direct_deps = []
        for dep in deps:
            skill_name_from_id = skill_lookup.get(str(dep.skill_id))
            if skill_name_from_id == skill_name:
                prereq_name = skill_lookup.get(str(dep.prerequisite_skill_id))
                if prereq_name:
                    direct_deps.append({
                        "skill": skill_name,
                        "prerequisite": prereq_name,
                        "strength": dep.strength,
                        "source_reference": dep.source_reference,
                    })

        return direct_deps

    async def get_all_dependencies(self) -> list[dict[str, Any]]:
        """Return all skill dependencies in the graph."""
        from app.models.profile import Skill

        result = await self.session.execute(select(SkillDependency))
        deps = result.scalars().all()

        skill_lookup = {}
        skill_result = await self.session.execute(select(Skill))
        for s in skill_result.scalars().all():
            skill_lookup[str(s.id)] = s.name

        all_deps = []
        for dep in deps:
            skill_name = skill_lookup.get(str(dep.skill_id))
            prereq_name = skill_lookup.get(str(dep.prerequisite_skill_id))
            if skill_name and prereq_name:
                all_deps.append({
                    "skill": skill_name,
                    "prerequisite": prereq_name,
                    "strength": dep.strength,
                    "source_reference": dep.source_reference,
                })

        return all_deps

    def build_graph(
        self, dependencies: list[dict[str, str]]
    ) -> dict[str, list[str]]:
        """Build an adjacency list from dependency edges.

        Each entry maps a skill to its list of prerequisites.
        """
        graph: dict[str, list[str]] = defaultdict(list)
        for dep in dependencies:
            graph[dep["skill"]].append(dep["prerequisite"])
        return dict(graph)

    def detect_cycles(self, graph: dict[str, list[str]]) -> bool:
        """Detect if the dependency graph has any cycles using DFS."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[str, int] = {node: WHITE for node in graph}

        # Ensure all nodes are in color map (including prerequisites not in graph keys)
        for node, prereqs in graph.items():
            for prereq in prereqs:
                if prereq not in color:
                    color[prereq] = WHITE

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for prereq in graph.get(node, []):
                if color.get(prereq, WHITE) == WHITE:
                    if dfs(prereq):
                        return True
                elif color.get(prereq, WHITE) == GRAY:
                    return True
            color[node] = BLACK
            return False

        for node in list(color.keys()):
            if color[node] == WHITE:
                if dfs(node):
                    return True
        return False

    def prerequisite_closure(
        self, skill: str, graph: dict[str, list[str]]
    ) -> set[str]:
        """Return the full set of transitive prerequisites for a skill."""
        visited: set[str] = set()
        stack = [skill]
        while stack:
            current = stack.pop()
            for prereq in graph.get(current, []):
                if prereq not in visited:
                    visited.add(prereq)
                    stack.append(prereq)
        return visited

    def is_prerequisite_satisfied(
        self,
        skill: str,
        graph: dict[str, list[str]],
        known_skills: set[str],
    ) -> bool:
        """Check if all prerequisites for a skill are in known_skills."""
        prereqs = graph.get(skill, [])
        return all(p in known_skills for p in prereqs)

    def topological_sort(
        self, graph: dict[str, list[str]]
    ) -> list[str]:
        """Return a topological ordering of skills (prerequisites first).

        Uses Kahn's algorithm. Returns skills in dependency order.
        Ties are broken alphabetically for determinism.
        """
        # Build in-degree count
        in_degree: dict[str, int] = defaultdict(int)
        all_nodes: set[str] = set()

        for node, prereqs in graph.items():
            all_nodes.add(node)
            for prereq in prereqs:
                all_nodes.add(prereq)
                in_degree[node] += 1
            if node not in in_degree:
                in_degree[node] = 0

        for node in all_nodes:
            if node not in in_degree:
                in_degree[node] = 0

        # Kahn's algorithm with alphabetical tie-breaking
        queue = sorted([n for n in all_nodes if in_degree[n] == 0])
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            # Find all nodes that depend on this node
            dependents = sorted(
                [n for n, prereqs in graph.items() if node in prereqs]
            )
            for dependent in dependents:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    queue.sort()

        return result


__all__ = ["SkillDependencyService"]
