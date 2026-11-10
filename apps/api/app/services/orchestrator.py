"""Application-level agent orchestrator.

The orchestrator is the outer boundary for agent execution. It decides which
capability is needed, which agent should run, creates an agent run, executes
the LangGraph workflow, records events, and returns structured output.

LangGraph executes the stateful workflow; the orchestrator remains in charge of
routing and run lifecycle.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID, uuid4

from app.core.llm import FakeLLMProvider, LLMProvider
from app.services.repositories import AgentRunRepository
from app.services.trace import TraceService
from app.tools import tool_registry
from app.tools.career_tools import (
    build_get_career_tool,
    build_get_career_recommendations_tool,
    build_get_career_requirements_tool,
    build_list_careers_tool,
    build_calculate_skill_match_tool,
)
from app.tools.evidence_tools import (
    build_get_evidence_tool,
    build_get_claim_evidence_tool,
    build_search_evidence_tool,
    build_verify_claim_tool,
)
from app.tools.learning_tools import (
    build_generate_learning_roadmap_tool,
    build_get_learning_resources_tool,
    build_get_roadmap_tool,
    build_get_skill_dependencies_tool,
)
from app.tools.interview_tools import (
    build_create_interview_session_tool,
    build_evaluate_interview_answer_tool,
    build_get_interview_results_tool,
    build_get_interview_session_tool,
    build_get_next_interview_question_tool,
    build_submit_interview_answer_tool,
)
from app.tools.careertwin_tools import (
    build_calculate_career_readiness_tool,
    build_get_careertwin_conflicts_tool,
    build_get_careertwin_insights_tool,
    build_get_careertwin_state_tool,
    build_get_stale_derived_state_tool,
    build_refresh_careertwin_state_tool,
)
from app.tools.profile_tool import build_get_profile_tool
from app.workflows.agent_workflow import AgentWorkflow

# Deterministic capability -> agent routing (no LLM router in this phase).
CAPABILITY_TO_AGENT: dict[str, str] = {
    "profile_summary": "profile_agent",
    "career_analysis": "career_agent",
    "skill_gap": "skill_gap_agent",
    "learning_plan": "learning_agent",
    "interview": "interview_agent",
    "evidence_check": "evidence_agent",
    "evidence_verification": "evidence_agent",
    "learning_roadmap": "learning_agent",
    "careertwin_analysis": "careertwin_agent",
}


_SLUG_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)+")


def extract_career_slug(user_input: str | None) -> str:
    """Return a career slug from free-form agent input.

    Accepts a bare slug (``machine-learning-engineer``), ``career_slug=<slug>``
    or a sentence that contains a slug. Returns an empty string when none is
    found so callers can fail with a clear message.
    """
    text = (user_input or "").strip().lower()
    if not text:
        return ""
    if text.startswith("career_slug="):
        text = text.split("=", 1)[1].strip()
    if _SLUG_TOKEN.fullmatch(text):
        return text
    matches = _SLUG_TOKEN.findall(text)
    return matches[-1] if matches else text


class AgentOrchestrator:
    """Orchestrates agent execution for application-level requests."""

    def __init__(
        self,
        *,
        session=None,
        trace_service: TraceService | None = None,
        llm_provider: LLMProvider | None = None,
        workflow: AgentWorkflow | None = None,
    ) -> None:
        self.session = session
        self.trace = trace_service or TraceService(session)
        self.llm_provider = llm_provider or FakeLLMProvider()
        self.workflow = workflow or AgentWorkflow(trace_service=self.trace)

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    async def run_capability(
        self,
        *,
        capability: str,
        profile_id: str | None = None,
        request_id: str | None = None,
        user_input: str = "",
    ) -> dict[str, Any]:
        """Execute a capability end-to-end and return a structured result.

        If the capability is unsupported, no run is created and a FAILED result
        is returned immediately.
        """
        request_id = request_id or uuid4().hex
        profile_id_uuid: UUID | None = None
        if profile_id:
            try:
                profile_id_uuid = UUID(profile_id)
            except ValueError:
                profile_id_uuid = None

        # Validate the capability before creating a run. Unsupported
        # capabilities are rejected without persisting a run.
        try:
            agent_name = self._select_agent(capability)
        except ValueError as exc:
            return {
                "run_id": None,
                "status": "FAILED",
                "agent": None,
                "error": str(exc),
            }

        # Register the get_profile tool bound to this request's session so the
        # Profile Agent can retrieve the profile. Only registered tools may run.
        if self.session is not None:
            tool_registry.register(build_get_profile_tool(self.session))

        # Register career tools for career-related capabilities.
        if self.session is not None and capability in (
            "career_analysis",
            "skill_gap",
            "career_recommendations",
        ):
            tool_registry.register(build_get_career_tool(self.session))
            tool_registry.register(build_list_careers_tool(self.session))
            tool_registry.register(build_get_career_requirements_tool(self.session))
            tool_registry.register(build_calculate_skill_match_tool(self.session))
            if capability == "career_recommendations":
                tool_registry.register(
                    build_get_career_recommendations_tool(self.session)
                )

        # Register evidence tools for evidence-related capabilities.
        if self.session is not None and capability in (
            "evidence_verification",
            "evidence_check",
        ):
            tool_registry.register(build_get_evidence_tool(self.session))
            tool_registry.register(build_search_evidence_tool(self.session))
            tool_registry.register(build_verify_claim_tool(self.session))
            tool_registry.register(build_get_claim_evidence_tool(self.session))

        # Register learning tools for learning_roadmap capability.
        if self.session is not None and capability in ("learning_roadmap", "learning_plan"):
            tool_registry.register(build_get_learning_resources_tool(self.session))
            tool_registry.register(build_get_skill_dependencies_tool(self.session))
            tool_registry.register(build_generate_learning_roadmap_tool(self.session))
            tool_registry.register(build_get_roadmap_tool(self.session))

        # Register interview tools for interview capability.
        if self.session is not None and capability == "interview":
            tool_registry.register(build_create_interview_session_tool(self.session))
            tool_registry.register(build_get_interview_session_tool(self.session))
            tool_registry.register(build_get_next_interview_question_tool(self.session))
            tool_registry.register(build_submit_interview_answer_tool(self.session))
            tool_registry.register(build_evaluate_interview_answer_tool(self.session))
            tool_registry.register(build_get_interview_results_tool(self.session))

        # Register careertwin tools for careertwin_analysis capability.
        if self.session is not None and capability == "careertwin_analysis":
            tool_registry.register(build_get_careertwin_state_tool(self.session))
            tool_registry.register(build_calculate_career_readiness_tool(self.session))
            tool_registry.register(build_get_careertwin_insights_tool(self.session))
            tool_registry.register(build_get_careertwin_conflicts_tool(self.session))
            tool_registry.register(build_get_stale_derived_state_tool(self.session))
            tool_registry.register(build_refresh_careertwin_state_tool(self.session))

        # Create the run and record RUN_STARTED and AGENT_STARTED.
        run = await self.trace.start_run(
            request_id=request_id,
            capability=capability,
            profile_id=profile_id_uuid,
            provider=self.llm_provider.provider_name,
            model=getattr(self.llm_provider, "model", None),
        )
        await self.trace.emit(
            run_id=run.id,
            event_type=self.trace.EVENT_AGENT_STARTED,
            agent_name=agent_name,
            message=f"Agent '{agent_name}' started for capability '{capability}'.",
        )

        try:
            # Build context: pass career_slug for career-related capabilities.
            context: dict[str, Any] = {}
            if profile_id:
                context["profile_id"] = profile_id
            if capability in ("career_analysis", "skill_gap"):
                context["career_slug"] = extract_career_slug(user_input)
            elif capability == "career_recommendations":
                context["profile_id"] = profile_id
            elif capability in ("evidence_verification", "evidence_check"):
                context["profile_id"] = profile_id
                context["input_text"] = user_input
            elif capability in ("learning_roadmap", "learning_plan"):
                context["profile_id"] = profile_id
                context["career_slug"] = extract_career_slug(user_input)
                context["profile_skills"] = []
            elif capability == "interview":
                context["profile_id"] = profile_id
                context["capability"] = user_input or "create_session"
                if context["capability"] == "create_session":
                    # Default tool input so the Interview Agent can open a session.
                    context["tool_input"] = {"profile_id": profile_id}
            elif capability == "careertwin_analysis":
                context["profile_id"] = profile_id
                context["active_target_career"] = user_input

            final_state = await self.workflow.run(
                current_agent=agent_name,
                profile_id=profile_id,
                request_id=request_id,
                run_id=str(run.id),
                user_input=user_input,
                context=context,
            )

            if final_state.status == "FAILED":
                error_msg = (
                    final_state.errors[-1]["message"]
                    if final_state.errors
                    else "Workflow failed"
                )
                await self.trace.fail_run(
                    run,
                    error=error_msg,
                )
                # Emit AGENT_FAILED.
                await self.trace.emit(
                    run_id=run.id,
                    event_type=self.trace.EVENT_AGENT_FAILED,
                    agent_name=agent_name,
                    message=f"Agent '{agent_name}' failed: {error_msg}",
                )
                return {
                    "run_id": str(run.id),
                    "status": "FAILED",
                    "error": run.error,
                    "agent_outputs": final_state.agent_outputs,
                    "agent": agent_name,
                }

            agent_output = final_state.agent_outputs.get(agent_name)
            await self.trace.complete_run(
                run,
                message=f"Capability '{capability}' completed by {agent_name}.",
                payload={"agent": agent_name, "capability": capability},
            )
            # Emit AGENT_COMPLETED.
            await self.trace.emit(
                run_id=run.id,
                event_type=self.trace.EVENT_AGENT_COMPLETED,
                agent_name=agent_name,
                message=f"Agent '{agent_name}' completed successfully.",
                payload={"agent_output": agent_output},
            )
            return {
                "run_id": str(run.id),
                "status": "COMPLETED",
                "agent": agent_name,
                "result": agent_output,
                "error": None,
            }

        except Exception as exc:  # noqa: BLE001 - structured failure
            await self.trace.fail_run(run, error=str(exc))
            await self.trace.emit(
                run_id=run.id,
                event_type=self.trace.EVENT_AGENT_FAILED,
                agent_name=agent_name,
                message=f"Agent '{agent_name}' raised: {exc}",
            )
            return {
                "run_id": str(run.id),
                "status": "FAILED",
                "error": str(exc),
                "agent": agent_name,
            }

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _select_agent(self, capability: str) -> str:
        agent_name = CAPABILITY_TO_AGENT.get(capability)
        if agent_name is None:
            raise ValueError(f"Unsupported capability: {capability}")
        return agent_name

    @classmethod
    def supported_capabilities(cls) -> list[str]:
        return sorted(CAPABILITY_TO_AGENT.keys())
