"""CareerTwin Agent — real implementation for unified intelligence.

Produces a typed explanation layer over deterministic CareerTwin state.
LLM may generate narrative/explanations; deterministic services calculate
all scores, insights, conflicts, and state.
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.contracts import AgentResult, AgentState, AgentStatus
from app.core.llm import FakeLLMProvider, LLMProvider
from app.services.careertwin_service import CareerTwinStateService
from app.tools import tool_registry


class CareerTwinAgent:
    """CareerTwin Agent — unified intelligence explanation."""

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

            output = {
                "capability": "careertwin_analysis",
                "state": state_data,
                "insights": state_data.get("insights", []),
                "conflicts": state_data.get("conflicts", []),
                "readiness_level": state_data.get("readiness_level", "NOT_READY"),
                "readiness_score": state_data.get("readiness_score", 0.0),
                "methodology": (
                    "Deterministic CareerTwin aggregation: profile + career fit + "
                    "skill gaps + roadmap + interview performance + evidence. "
                    "Insights and conflicts derived from structured signals."
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


__all__ = ["CareerTwinAgent"]
