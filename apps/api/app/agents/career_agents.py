"""Real agent implementations for Career and Skill Gap.

These agents use deterministic tools and services, with the LLM provider used
only for interpretation/polishing — never for calculating scores or inventing
career requirements.
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.contracts import AgentResult, AgentState, AgentStatus
from app.agents.schemas import CareerAnalysis, SkillGapAnalysis
from app.core.llm import FakeLLMProvider, LLMProvider
from app.services.career_fit_service import compute_career_fit
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.skill_matching import compute_skill_match
from app.tools import tool_registry

TOOL_REQUEST_KEY = "tool_requested"
TOOL_INPUT_KEY = "tool_input"


class CareerAgent:
    """Career Agent — interprets deterministic career fit results.

    Workflow:
    1. Request get_profile tool (no profile data yet).
    2. Request get_career tool (no career data yet).
    3. Request calculate_skill_match tool (no match data yet).
    4. On final invocation, build typed CareerAnalysis from real data.
    """

    name = "career_agent"

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        tool_registry_instance=None,
    ) -> None:
        self.llm_provider = llm_provider or FakeLLMProvider()
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

            # Step 1: request get_profile if we lack profile data
            profile_data = state.tool_results.get("get_profile")
            if profile_data is None:
                state.context[TOOL_REQUEST_KEY] = "get_profile"
                state.context[TOOL_INPUT_KEY] = {"profile_id": profile_id}
                state.context["profile_id"] = profile_id
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.RUNNING,
                    output=None,
                    metadata={"provider": self.llm_provider.provider_name},
                    errors=errors,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                )

            # Step 2: request get_career if we lack career data
            career_data = state.tool_results.get("get_career")
            if career_data is None:
                state.context[TOOL_REQUEST_KEY] = "get_career"
                state.context[TOOL_INPUT_KEY] = {"slug": career_slug}
                state.context["career_slug"] = career_slug
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.RUNNING,
                    output=None,
                    metadata={"provider": self.llm_provider.provider_name},
                    errors=errors,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                )

            # Step 3: request calculate_skill_match if we lack match data
            match_data = state.tool_results.get("calculate_skill_match")
            if match_data is None:
                state.context[TOOL_REQUEST_KEY] = "calculate_skill_match"
                state.context[TOOL_INPUT_KEY] = {
                    "career_id": career_data["id"],
                    "career_title": career_data["title"],
                    "career_skills": career_data.get("skills", []),
                    "profile_skills": profile_data.get("skills", []),
                }
                state.context["career_id"] = career_data["id"]
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.RUNNING,
                    output=None,
                    metadata={"provider": self.llm_provider.provider_name},
                    errors=errors,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                )

            # Step 4: build typed CareerAnalysis from real data
            from app.services.career_fit_service import compute_career_fit

            match_result = compute_skill_match(
                career_id=str(career_data["id"]),
                career_title=career_data["title"],
                career_skills=career_data.get("skills", []),
                profile_skills=profile_data.get("skills", []),
            )

            fit_result = compute_career_fit(
                career_id=str(career_data["id"]),
                career_title=career_data["title"],
                match_result=match_result,
            )

            # Use LLM provider only to polish the fit_summary text — never
            # to invent facts or override the deterministic score.
            polished_summary = await self._polish_summary(
                fit_result.fit_summary, match_result
            )
            fit_result.fit_summary = polished_summary or fit_result.fit_summary

            output = CareerAnalysis(
                career_id=str(career_data["id"]),
                career_title=career_data["title"],
                fit_score=fit_result.fit_score,
                fit_summary=fit_result.fit_summary,
                strengths=fit_result.strengths,
                skill_gaps=fit_result.gaps,
                recommended_focus=[
                    m["skill_name"] for m in match_result.missing[:5]
                ],
                relevant_projects=[
                    p.get("description", "")
                    for p in career_data.get("projects", [])[:3]
                ],
                caveats=[
                    "Fit score is computed deterministically from skill "
                    "overlap; it does not guarantee job outcomes.",
                ],
                metadata={
                    "provider": self.llm_provider.provider_name,
                    "methodology": match_result.methodology,
                },
            ).model_dump()

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

    async def _polish_summary(
        self, summary: str, match_result: Any
    ) -> str:
        """Ask the LLM provider to refine the fit summary text.

        The provider only rewords; it never invents facts because the facts
        are already fixed in the deterministic result.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "Rewrite the following career fit summary into a concise, "
                    "professional paragraph. Do not add facts or numbers that "
                    "are not present in the source summary. Return only the "
                    "rewritten text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source summary: {summary}\n"
                    f"Overall score: {match_result.overall_score:.0%}\n"
                    f"Matched skills: {len(match_result.matched)}\n"
                    f"Missing skills: {len(match_result.missing)}"
                ),
            },
        ]
        try:
            response = await self.llm_provider.generate(messages)
            return response.content or summary
        except Exception:
            return summary


class SkillGapAgent:
    """Skill Gap Agent — explains and prioritizes deterministic skill gaps.

    Workflow:
    1. Request get_profile tool.
    2. Request get_career tool.
    3. Request calculate_skill_match tool.
    4. Build typed SkillGapAnalysis from real match data.
    """

    name = "skill_gap_agent"

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        tool_registry_instance=None,
    ) -> None:
        self.llm_provider = llm_provider or FakeLLMProvider()
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

            # Step 1: request get_profile
            profile_data = state.tool_results.get("get_profile")
            if profile_data is None:
                state.context[TOOL_REQUEST_KEY] = "get_profile"
                state.context[TOOL_INPUT_KEY] = {"profile_id": profile_id}
                state.context["profile_id"] = profile_id
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.RUNNING,
                    output=None,
                    metadata={"provider": self.llm_provider.provider_name},
                    errors=errors,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                )

            # Step 2: request get_career
            career_data = state.tool_results.get("get_career")
            if career_data is None:
                state.context[TOOL_REQUEST_KEY] = "get_career"
                state.context[TOOL_INPUT_KEY] = {"slug": career_slug}
                state.context["career_slug"] = career_slug
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.RUNNING,
                    output=None,
                    metadata={"provider": self.llm_provider.provider_name},
                    errors=errors,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                )

            # Step 3: request calculate_skill_match
            match_data = state.tool_results.get("calculate_skill_match")
            if match_data is None:
                state.context[TOOL_REQUEST_KEY] = "calculate_skill_match"
                state.context[TOOL_INPUT_KEY] = {
                    "career_id": career_data["id"],
                    "career_title": career_data["title"],
                    "career_skills": career_data.get("skills", []),
                    "profile_skills": profile_data.get("skills", []),
                }
                state.context["career_id"] = career_data["id"]
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.RUNNING,
                    output=None,
                    metadata={"provider": self.llm_provider.provider_name},
                    errors=errors,
                    duration_ms=int((time.perf_counter() - start) * 1000),
                )

            # Step 4: build typed SkillGapAnalysis from real match data
            match_result = compute_skill_match(
                career_id=str(career_data["id"]),
                career_title=career_data["title"],
                career_skills=career_data.get("skills", []),
                profile_skills=profile_data.get("skills", []),
            )

            # Prioritize gaps by importance (CORE > IMPORTANT > SUPPORTING)
            importance_order = {"CORE": 0, "IMPORTANT": 1, "SUPPORTING": 2}
            sorted_missing = sorted(
                match_result.missing,
                key=lambda m: (
                    importance_order.get(m.get("importance", "SUPPORTING"), 99),
                    m.get("skill_name", ""),
                ),
            )

            priority_gaps = []
            for m in sorted_missing[:8]:
                priority = (
                    "P0" if m.get("importance") == "CORE"
                    else "P1" if m.get("importance") == "IMPORTANT"
                    else "P2"
                )
                priority_gaps.append(
                    {
                        "skill": m["skill_name"],
                        "importance": m.get("importance"),
                        "current_level": m.get("user_level"),
                        "required_level": m.get("required_level"),
                        "priority": priority,
                        "reason": m.get("reason", ""),
                    }
                )

            matched_strengths = [
                {
                    "skill": m["skill_name"],
                    "importance": m.get("importance"),
                    "user_level": m.get("user_level"),
                }
                for m in match_result.matched[:8]
            ]

            recommendations = []
            for gap in priority_gaps[:5]:
                recommendations.append(
                    f"Develop {gap['skill']} ({gap['importance'].lower()}) "
                    f"— currently {gap['current_level'] or 'not listed'}, "
                    f"role expects {gap['required_level'] or 'unspecified'}."
                )

            output = SkillGapAnalysis(
                career_id=str(career_data["id"]),
                career_title=career_data["title"],
                overall_score=match_result.overall_score,
                priority_gaps=[
                    f"{g['skill']} ({g['priority']}): {g['reason']}"
                    for g in priority_gaps
                ],
                matched_strengths=[
                    f"{s['skill']} ({s['importance']}) — {s['user_level'] or 'not specified'}"
                    for s in matched_strengths
                ],
                recommendations=recommendations,
                caveats=[
                    "Gap priorities are determined deterministically by skill "
                    "importance and proficiency gap; the LLM does not assign "
                    "priority scores.",
                ],
                metadata={
                    "provider": self.llm_provider.provider_name,
                    "methodology": match_result.methodology,
                },
            ).model_dump()

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


__all__ = [
    "CareerAgent",
    "SkillGapAgent",
]
