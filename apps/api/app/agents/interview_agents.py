"""Real agent implementation for adaptive interviews.

The Interview Agent orchestrates:
session state → question selection → question generation if needed →
answer evaluation → skill performance update → next-question decision →
completion summary

LLM responsibilities:
- question wording
- qualitative evaluation
- feedback generation

Deterministic responsibilities:
- state
- selection
- difficulty
- scoring aggregation
- completion
- progression
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.contracts import AgentResult, AgentState, AgentStatus
from app.core.llm import FakeLLMProvider, LLMProvider
from app.tools import tool_registry


class InterviewAgent:
    """Interview Agent — adaptive interview orchestration."""

    name = "interview_agent"

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
            capability = state.context.get("capability", "interview")
            session_id = state.context.get("session_id")
            profile_id = state.profile_id or state.context.get("profile_id")

            if capability == "create_session":
                # Create a new interview session.
                tool = self.tool_registry.get("create_interview_session")
                if tool is None:
                    raise ValueError("create_interview_session tool not registered.")
                result = await tool.execute(
                    state.context.get("tool_input", {})
                )
                if not result.success:
                    raise ValueError(result.error or "Session creation failed.")
                output = result.output
                status = AgentStatus.COMPLETED

            elif capability == "get_next_question":
                tool = self.tool_registry.get("get_next_interview_question")
                if tool is None:
                    raise ValueError("get_next_interview_question tool not registered.")
                result = await tool.execute(
                    state.context.get("tool_input", {})
                )
                if not result.success:
                    raise ValueError(result.error or "Question retrieval failed.")
                output = result.output
                status = AgentStatus.COMPLETED

            elif capability == "submit_answer":
                tool = self.tool_registry.get("submit_interview_answer")
                if tool is None:
                    raise ValueError("submit_interview_answer tool not registered.")
                result = await tool.execute(
                    state.context.get("tool_input", {})
                )
                if not result.success:
                    raise ValueError(result.error or "Answer submission failed.")
                output = result.output
                status = AgentStatus.COMPLETED

            elif capability == "get_results":
                tool = self.tool_registry.get("get_interview_results")
                if tool is None:
                    raise ValueError("get_interview_results tool not registered.")
                result = await tool.execute(
                    state.context.get("tool_input", {})
                )
                if not result.success:
                    raise ValueError(result.error or "Results retrieval failed.")
                output = result.output
                status = AgentStatus.COMPLETED

            else:
                raise ValueError(f"Unknown interview capability: {capability}")

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


__all__ = ["InterviewAgent"]
