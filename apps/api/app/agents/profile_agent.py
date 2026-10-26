"""Profile Agent — contract and deterministic stub.

The Profile Agent interprets and summarizes profile information. It retrieves
the profile through the registered ``get_profile`` tool rather than receiving
the profile as an unstructured prompt from the API layer.

Workflow within LangGraph:

1. First invocation: requests the ``get_profile`` tool (no profile data yet).
2. Workflow executes the tool and feeds the result back into state.
3. Second invocation: builds a typed ``ProfileSummary`` from the *real*
   retrieved profile data. Nothing is fabricated — absent information is listed
   explicitly in ``missing_information``.

The LLM provider abstraction is used to polish the overview text, keeping the
provider boundary intact even though the stub could run without it.
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.contracts import AgentResult, AgentState, AgentStatus
from app.agents.schemas import ProfileSummary
from app.core.llm import FakeLLMProvider, LLMProvider
from app.tools import tool_registry
from app.tools.profile_tool import GetProfileInput

TOOL_REQUEST_KEY = "tool_requested"
TOOL_INPUT_KEY = "tool_input"


class ProfileAgent:
    """Profile Agent stub.

    Retrieves the profile via the registered ``get_profile`` tool and produces
    a typed ``ProfileSummary``. Real interpretation/reconciliation logic is
    added in a later phase when the Profile Agent is backed by an LLM.
    """

    name = "profile_agent"

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
            if not profile_id:
                raise ValueError("No profile_id available in agent state.")

            # --- Step 1: request the get_profile tool if we lack data ---------
            profile_data = state.tool_results.get("get_profile")
            if profile_data is None:
                state.context[TOOL_REQUEST_KEY] = "get_profile"
                state.context[TOOL_INPUT_KEY] = {"profile_id": profile_id}
                state.context["profile_id"] = profile_id
                duration_ms = int((time.perf_counter() - start) * 1000)
                return AgentResult(
                    agent_name=self.name,
                    status=AgentStatus.RUNNING,
                    output=None,
                    metadata={"provider": self.llm_provider.provider_name},
                    errors=errors,
                    duration_ms=duration_ms,
                )

            # --- Step 2: build the summary from REAL profile data -------------
            summary = self._build_summary(profile_id, profile_data, state.user_input)

            # Use the LLM provider to polish the overview text. The provider is
            # fake/deterministic in this phase; real providers implement the same
            # protocol. We never let the provider fabricate profile facts because
            # the facts are already fixed in ``summary``. ProfileSummary is frozen,
            # so we create a new instance with the polished overview.
            overview_text = await self._polish_overview(
                summary, state.user_input
            )
            summary = ProfileSummary(
                profile_id=summary.profile_id,
                overview=overview_text or summary.overview,
                strengths=summary.strengths,
                notable_skills=summary.notable_skills,
                experience_highlights=summary.experience_highlights,
                missing_information=summary.missing_information,
                metadata=summary.metadata,
            )

            output = summary.model_dump()
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_summary(
        self, profile_id: str, profile_data: dict[str, Any], user_input: str
    ) -> ProfileSummary:
        """Build a ProfileSummary strictly from retrieved profile data.

        No information is fabricated. Missing/ambiguous fields are reported in
        ``missing_information``.
        """
        full_name = profile_data.get("full_name") or "Unknown"
        headline = profile_data.get("headline")
        summary_text = profile_data.get("summary")
        skills = profile_data.get("skills") or []
        education = profile_data.get("education") or []
        projects = profile_data.get("projects") or []
        experience = profile_data.get("experience") or []
        career_goals = profile_data.get("career_goals") or []

        strengths: list[str] = []
        notable_skills: list[str] = [s.get("name", "") for s in skills if s.get("name")]
        experience_highlights: list[str] = []
        missing_information: list[str] = []

        if not full_name or full_name == "Unknown":
            missing_information.append("Full name")
        if headline:
            strengths.append(f"Clear headline: {headline}")
        else:
            missing_information.append("Headline")
        if summary_text:
            strengths.append("Profile summary provided")
        else:
            missing_information.append("Summary")
        if skills:
            strengths.append(f"{len(skills)} skill(s) on record")
        else:
            missing_information.append("Skills")
        if experience:
            experience_highlights.append(
                f"{len(experience)} experience record(s) on file"
            )
            for exp in experience[:3]:
                role = exp.get("role")
                org = exp.get("organization")
                if role and org:
                    experience_highlights.append(f"{role} at {org}")
        else:
            missing_information.append("Experience")
        if projects:
            experience_highlights.append(f"{len(projects)} project(s) on file")
        if career_goals:
            strengths.append(f"{len(career_goals)} career goal(s) defined")
        else:
            missing_information.append("Career goals")

        overview = (
            f"Profile for {full_name}. "
            f"{len(skills)} skill(s), {len(experience)} experience record(s), "
            f"{len(projects)} project(s), and {len(education)} education record(s) on file."
        )

        return ProfileSummary(
            profile_id=profile_id,
            overview=overview,
            strengths=strengths,
            notable_skills=[s for s in notable_skills if s],
            experience_highlights=experience_highlights,
            missing_information=missing_information,
            metadata={"user_input": user_input[:100]},
        )

    async def _polish_overview(
        self, summary: ProfileSummary, user_input: str
    ) -> str:
        """Ask the LLM provider to refine the overview text.

        The provider only rewords; it never invents profile facts because the
        facts are already fixed in ``summary``.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    "Rewrite the following profile overview into a concise, "
                    "professional summary. Do not add facts that are not present "
                    "in the source overview. Return only the rewritten text."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Source overview: {summary.overview}\n"
                    f"Notable skills: {', '.join(summary.notable_skills) or 'none'}\n"
                    f"User request: {user_input}"
                ),
            },
        ]
        try:
            response = await self.llm_provider.generate(messages)
            return response.content or summary.overview
        except Exception:
            return summary.overview


__all__ = ["ProfileAgent"]
