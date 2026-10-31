"""CareerTwin Agent â€” real implementation for unified intelligence.

Produces a typed explanation layer over deterministic CareerTwin state.
LLM may generate narrative/explanations; deterministic services calculate
all scores, insights, conflicts, and state.
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.contracts import AgentResult, AgentState, AgentStatus
from app.core.llm import FakeLLMProvider, LLMProvider
from app.schemas.careertwin import CareerTwinNarrative, CareerTwinState
from app.services.careertwin_service import CareerTwinStateService
from app.tools import tool_registry




class CareerTwinAgent:
    """CareerTwin Agent â€” unified intelligence explanation."""

    name = "careertwin_agent"

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
            if not profile_id:
                raise ValueError("No profile_id available in agent state.")

            active_target_career = state.context.get("active_target_career")

            # Step 1: request get_careertwin_state tool.
            tool = self.tool_registry.get("get_careertwin_state")
            if tool is None:
                raise ValueError("get_careertwin_state tool not registered.")
            result = await tool.execute({
                "profile_id": profile_id,
                "active_target_career": active_target_career,
            })
            if not result.success:
                raise ValueError(result.error or "State retrieval failed.")

            state_data = result.output.get("state", {})

            # Generate LLM narrative (explanation only, never affects scores).
            narrative = await self._generate_narrative(state_data)

            output = {
                "capability": "careertwin_analysis",
                "state": state_data,
                "insights": state_data.get("insights", []),
                "conflicts": state_data.get("conflicts", []),
                "readiness_level": state_data.get("readiness_level", "NOT_READY"),
                "readiness_score": state_data.get("readiness_score", 0.0),
                "narrative": narrative.model_dump() if narrative else None,
                "methodology": (
                    "Deterministic CareerTwin aggregation: profile + career fit + "
                    "skill gaps + roadmap + interview performance + evidence. "
                    "Insights and conflicts derived from structured signals. "
                    "Narrative is LLM-generated explanation only."
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


    async def _generate_narrative(
        self, state_data: dict[str, Any]
    ) -> CareerTwinNarrative | None:
        """Generate a personalized narrative using the LLM provider.

        Returns None if the LLM fails or returns malformed output.
        The narrative is explanation only — it never affects scores.
        """
        readiness = state_data.get("readiness_level", "NOT_READY")
        fit_score = 0.0
        career_fit = state_data.get("career_fit")
        if career_fit:
            fit_score = career_fit.get("fit_score", 0.0)
        career_title = ""
        if career_fit:
            career_title = career_fit.get("career_title", "")

        gaps = state_data.get("skill_gaps", [])
        missing_gaps = [g.get("skill_name", "") for g in gaps if g.get("status") == "MISSING"]
        top_gaps = missing_gaps[:5]

        strengths = []
        if career_fit:
            strengths = career_fit.get("strongest_areas", [])

        interview = state_data.get("interview_summary", {})
        interview_weaknesses = interview.get("weaknesses", [])
        interview_obs = ""
        if interview_weaknesses:
            interview_obs = f"Interview performance suggests improvement needed in: {', '.join(interview_weaknesses[:3])}."
        else:
            interview_obs = "No interview weaknesses identified."

        roadmap = state_data.get("roadmap_summary", {})
        roadmap_obs = ""
        if roadmap.get("total_skills", 0) > 0:
            roadmap_obs = f"Roadmap has {roadmap['total_skills']} skills to learn ({roadmap.get('p0_count', 0)} critical)."
        else:
            roadmap_obs = "No roadmap generated yet."

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a career intelligence assistant. Generate a concise, "
                    "professional narrative about the user's career state. "
                    "Do not invent facts or scores. Only use the provided data. "
                    "Return a JSON object with keys: summary, current_position, "
                    "key_strengths, priority_gaps, recommended_next_actions, "
                    "interview_observation, roadmap_observation."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Readiness: {readiness}\n"
                    f"Fit score: {fit_score:.0%}\n"
                    f"Career: {career_title}\n"
                    f"Strengths: {', '.join(strengths[:5])}\n"
                    f"Priority gaps: {', '.join(top_gaps)}\n"
                    f"Interview weaknesses: {', '.join(interview_weaknesses[:5])}\n"
                    f"Roadmap: {roadmap.get('total_skills', 0)} skills, "
                    f"{roadmap.get('p0_count', 0)} critical"
                ),
            },
        ]

        try:
            response = await self.llm_provider.generate(
                messages, response_schema=CareerTwinNarrative
            )
            if response.structured_output:
                return CareerTwinNarrative.model_validate(response.structured_output)
        except Exception:
            pass

        # Deterministic fallback narrative.
        return CareerTwinNarrative(
            summary=f"Your career readiness is {readiness.replace('_', ' ').lower()}.",
            current_position=f"Fit score: {fit_score:.0%} for {career_title}.",
            key_strengths=strengths[:5],
            priority_gaps=top_gaps,
            recommended_next_actions=[
                f"Focus on {g}" for g in top_gaps[:3]
            ],
            interview_observation=interview_obs,
            roadmap_observation=roadmap_obs,
        )


__all__ = ["CareerTwinAgent"]
