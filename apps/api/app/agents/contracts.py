"""Agent state, result, and contract models.

These are application-level types used by agents, the orchestrator, and
LangGraph workflows. They are NOT vendor-specific.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(str):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ALL_STATUSES = (
    AgentStatus.PENDING,
    AgentStatus.RUNNING,
    AgentStatus.COMPLETED,
    AgentStatus.FAILED,
    AgentStatus.CANCELLED,
)


class AgentState(BaseModel):
    """Strongly typed state for an agent run.

    Compatible with LangGraph. Kept explicit — no arbitrary application state.
    """

    model_config = ConfigDict(frozen=False)

    run_id: str = Field(default_factory=lambda: uuid4().hex)
    profile_id: str | None = None
    request_id: str | None = None
    user_input: str = ""
    current_agent: str | None = None
    messages: list[dict[str, str]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    tool_results: dict[str, Any] = Field(default_factory=dict)
    agent_outputs: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    status: str = AgentStatus.PENDING

    def add_error(self, agent_name: str, code: str, message: str) -> None:
        self.errors.append(
            {"agent": agent_name, "code": code, "message": message}
        )


class AgentResult(BaseModel):
    """Common result structure returned by an agent."""

    model_config = ConfigDict(frozen=True)

    agent_name: str
    status: str
    output: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    duration_ms: int | None = None


class AgentProtocol(BaseModel):
    """Marker: all agents expose a stable name and a run method.

    Implemented as a Protocol structurally; this class documents the shape.
    """

    name: str

    async def run(self, state: AgentState) -> AgentResult:
        ...
