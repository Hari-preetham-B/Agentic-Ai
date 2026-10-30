"""Deterministic stubs for agents not yet implemented.

Learning and Interview agents remain as contract stubs in this phase.
Career, Skill Gap, and Evidence agents have real implementations in
career_agents.py and evidence_agents.py.
"""

from __future__ import annotations

import time
from typing import Any

from app.agents.contracts import AgentResult, AgentState, AgentStatus


class _StubAgent:
    """Base for deterministic agent stubs."""

    def __init__(self, name: str, capability: str) -> None:
        self.name = name
        self._capability = capability

    async def run(self, state: AgentState) -> AgentResult:
        start = time.perf_counter()
        output = {
            "capability": self._capability,
            "status": "not_implemented",
            "message": (
                f"The {self.name} is a contract stub in this phase. "
                "Real intelligence is added in a later phase."
            ),
        }
        duration_ms = int((time.perf_counter() - start) * 1000)
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            output=output,
            metadata={"stub": True},
            duration_ms=duration_ms,
        )


class InterviewAgent(_StubAgent):
    """Interview Agent — future: generate and evaluate interview questions."""
    name = "interview_agent"

    def __init__(self) -> None:
        super().__init__(self.name, "interview")


__all__ = [
    "LearningAgent",
]
