"""Application-level agent orchestrator.

The orchestrator is the outer boundary for agent execution. It decides which
capability is needed, which agent should run, creates an agent run, executes
the LangGraph workflow, records events, and returns structured output.

LangGraph executes the stateful workflow; the orchestrator remains in charge of
routing and run lifecycle.
"""

from __future__ import annotations

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
}


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
                context["career_slug"] = user_input or context.get(
                    "career_slug", ""
                )
                # If user_input looks like a slug, use it; otherwise the agent
                # will need the caller to have set it. We default user_input
                # to the slug when it matches a known career slug.
            elif capability == "career_recommendations":
                context["profile_id"] = profile_id

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
