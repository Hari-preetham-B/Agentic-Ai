"""LangGraph agent workflow.

A minimal, reusable stateful agent workflow. The application orchestrator
remains the outer boundary; LangGraph manages workflow state, nodes, and
conditional transitions.

Graph:

    START
      ↓
  agent_node
      ↓
  (tool requested?)
  ├─ yes → tool_node → agent_node
  └─ no  → END
        ↓
       END

The initial graph is deterministic enough to test and supports future
conditional multi-agent workflows.
"""

from __future__ import annotations

import uuid
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.agents.contracts import AgentState
from app.services.trace import TraceService
from app.tools import tool_registry


class AgentWorkflow:
    """Compiles and runs a LangGraph agent workflow."""

    def __init__(
        self,
        state_schema: type[AgentState] = AgentState,
        trace_service: TraceService | None = None,
    ) -> None:
        self.state_schema = state_schema
        self.trace = trace_service
        self.graph = self._build()
        self._current_run_id: str | None = None

    def _build(self):
        builder = StateGraph(self.state_schema)

        builder.add_node("agent_node", self._agent_node)
        builder.add_node("tool_node", self._tool_node)

        builder.add_edge(START, "agent_node")
        builder.add_conditional_edges(
            "agent_node",
            self._route_after_agent,
            {
                "tool": "tool_node",
                "end": END,
            },
        )
        builder.add_edge("tool_node", "agent_node")

        return builder.compile()

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    async def _agent_node(self, state: AgentState) -> dict[str, Any]:
        """Run the selected agent.

        The orchestrator sets ``state.current_agent`` before invoking the
        workflow. The agent runs and may request a tool by setting
        ``state.context["tool_requested"]``.
        """
        from app.agents import ProfileAgent
        from app.agents.career_agents import (
            CareerAgent,
            SkillGapAgent,
        )
        from app.agents.evidence_agents import EvidenceAgent
        from app.agents.interview_agents import InterviewAgent
        from app.agents.learning_agents import LearningAgent

        agent_map = {
            "profile_agent": ProfileAgent(),
            "career_agent": CareerAgent(),
            "skill_gap_agent": SkillGapAgent(),
            "learning_agent": LearningAgent(),
            "interview_agent": InterviewAgent(),
            "evidence_agent": EvidenceAgent(),
        }

        agent_name = state.current_agent or "profile_agent"
        agent = agent_map.get(agent_name)
        if agent is None:
            state.add_error("workflow", "UNKNOWN_AGENT", f"Unknown agent: {agent_name}")
            state.status = "FAILED"
            return {"status": state.status, "errors": state.errors}

        # Emit AGENT_STARTED via the trace service if available.
        run_id = self._current_run_id
        if self.trace is not None and run_id:
            await self.trace.emit(
                run_id=uuid.UUID(run_id),
                event_type=self.trace.EVENT_AGENT_STARTED,
                agent_name=agent_name,
                message=f"Agent '{agent_name}' started.",
            )

        result = await agent.run(state)

        # Merge agent output/errors into state.
        updates: dict[str, Any] = {}
        if result.errors:
            state.errors.extend(result.errors)
            updates["errors"] = state.errors
        if result.output:
            state.agent_outputs[agent_name] = result.output
            updates["agent_outputs"] = state.agent_outputs

        # Propagate the agent's status into the workflow state so that the
        # graph knows whether to continue (RUNNING) or finish (COMPLETED).
        state.status = result.status
        updates["status"] = state.status

        if result.status == "FAILED":
            return updates

        # The agent signals a tool request via state.context.
        tool_requested = state.context.get("tool_requested")
        if tool_requested:
            updates["context"] = state.context

        return updates

    async def _tool_node(self, state: AgentState) -> dict[str, Any]:
        """Execute a tool requested by the agent.

        Only registered tools may execute. Tool arguments were already
        validated by the tool's Pydantic schema.
        """
        tool_name = state.context.get("tool_requested")
        tool_input = state.context.get("tool_input", {})

        if not tool_name:
            state.add_error("workflow", "NO_TOOL_REQUESTED", "No tool requested.")
            state.status = "FAILED"
            return {"status": state.status, "errors": state.errors}

        tool = tool_registry.get(tool_name)
        if tool is None:
            state.add_error(
                "workflow",
                "UNKNOWN_TOOL",
                f"Tool '{tool_name}' is not registered.",
            )
            state.status = "FAILED"
            return {"status": state.status, "errors": state.errors}

        run_id = self._current_run_id

        if run_id is not None and self.trace is not None:
            await self.trace.emit(
                run_id=uuid.UUID(run_id),
                event_type=self.trace.EVENT_TOOL_STARTED,
                tool_name=tool_name,
                message=f"Tool '{tool_name}' started.",
            )

        result = await tool.execute(tool_input)

        # Store result and clear the tool request so the agent runs again.
        state.tool_results[tool_name] = result.output if result.success else None
        state.context.pop("tool_requested", None)
        state.context.pop("tool_input", None)

        updates: dict[str, Any] = {
            "tool_results": state.tool_results,
            "context": state.context,
        }

        if run_id is not None and self.trace is not None:
            if result.success:
                await self.trace.emit(
                    run_id=run_id,
                    event_type=self.trace.EVENT_TOOL_COMPLETED,
                    tool_name=tool_name,
                    message=f"Tool '{tool_name}' completed.",
                    payload={"output_keys": list((result.output or {}).keys())},
                )
            else:
                await self.trace.emit(
                    run_id=run_id,
                    event_type=self.trace.EVENT_AGENT_FAILED,
                    tool_name=tool_name,
                    message=f"Tool '{tool_name}' failed: {result.error}",
                    payload={"error": result.error},
                )

        if not result.success:
            state.add_error("workflow", "TOOL_FAILED", result.error or "Tool failed.")
            state.status = "FAILED"
            updates["errors"] = state.errors
            updates["status"] = state.status

        return updates

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    @staticmethod
    def _route_after_agent(state: AgentState) -> str:
        if state.status == "FAILED":
            return "end"
        if state.context.get("tool_requested"):
            return "tool"
        return "end"

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    async def run(
        self,
        *,
        current_agent: str,
        profile_id: str | None = None,
        request_id: str | None = None,
        run_id: str | None = None,
        user_input: str = "",
        context: dict[str, Any] | None = None,
    ) -> AgentState:
        """Execute the workflow and return the final state."""
        self._current_run_id = run_id or request_id
        initial_state = AgentState(
            current_agent=current_agent,
            profile_id=profile_id,
            request_id=request_id,
            user_input=user_input,
            context=context or {},
            status="RUNNING",
        )
        result = await self.graph.ainvoke(initial_state)  # type: ignore[no-any-return]
        # LangGraph may return a dict rather than the Pydantic state object.
        if isinstance(result, dict):
            return AgentState.model_validate(result)
        return result
