"""Real agent implementation for Learning Roadmap.

The Learning Agent orchestrates:
Profile / Career → Skill Gap → Dependencies → Priority Engine →
Resource Matching → Roadmap Generation → Evidence-aware explanation

The LLM may generate concise rationale, learning explanations, and
personalized descriptions. The LLM must NOT calculate skill gaps,
determine prerequisites, rank resources, determine roadmap ordering,
or assign confidence.
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.contracts import AgentResult, AgentState, AgentStatus
from app.core.llm import FakeLLMProvider, LLMProvider
from app.tools import tool_registry


class LearningAgent:
    """Learning Agent — generates dependency-aware career roadmaps."""

    name = "learning_agent"

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        session=None,
        tool_registry_instance=None,
    ) -> None:
        self.llm_provider = llm_provider or FakeLLMProvider()
        self.session = session
        self.tool_registry = tool_registry_instance or tool_registry

    async def run(self, state: AgentState) -> AgentResult:
        start = time.perf_counter()
        errors: list[dict[str, Any]] = []
        output: dict[str, Any] | None = None

        try:
            profile_id = state.profile_id or state.context.get("profile_id")
            career_slug = state.context.get("career_slug")
            if not profile_id:
                raise ValueError("No profile_id available in agent state.")
            if not career_slug:
                raise ValueError("No career_slug available in agent state.")

            # Step 1: request get_profile if we lack profile data.
            profile_data = state.tool_results.get("get_profile")
            if profile_data is None:
                state.context["tool_requested"] = "get_profile"
                state.context["tool_input"] = {"profile_id": profile_id}
                state.context["profile_id"] = profile_id
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.RUNNING,
                    output=None,
                    metadata={"provider": self.llm_provider.provider_name},
                    errors=errors,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                )

            # Step 2: extract profile skills.
            profile_skills = [
                {
                    "name": s.get("name"),
                    "proficiency": s.get("proficiency"),
                    "years_experience": s.get("years_experience"),
                    "source": s.get("source"),
                }
                for s in (profile_data.get("skills", []) or [])
            ]

            # Step 3: generate roadmap via tool.
            tool = self.tool_registry.get("generate_learning_roadmap")
            if tool is None:
                raise ValueError("generate_learning_roadmap tool not registered.")
            result = await tool.execute({
                "profile_id": profile_id,
                "career_slug": career_slug,
                "profile_skills": profile_skills,
            })
            if not result.success:
                raise ValueError(result.error or "Roadmap generation failed.")
            roadmap = result.output

            output = {
                "capability": "learning_roadmap",
                "roadmap_id": roadmap["roadmap_id"],
                "profile_id": roadmap["profile_id"],
                "career_id": roadmap["career_id"],
                "career_title": roadmap["career_title"],
                "items": roadmap["items"],
                "summary": roadmap["summary"],
                "methodology": (
                    "Deterministic roadmap generation: skill gaps from "
                    "SkillMatchingEngine, dependency graph traversal, "
                    "priority calculation (gap severity + career importance + "
                    "dependency centrality), topological sequencing, "
                    "resource matching by relevance/difficulty/effort."
                ),
            }

            status = AgentStatus.COMPLETED

        except Exception as exc:  # noqa: BLE001
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


__all__ = ["LearningAgent"]
