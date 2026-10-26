"""Execution trace service.

The trace service is the single persistence boundary for agent execution events.
Agents and workflows emit events through this service; raw database inserts are
never scattered throughout the agent layer.

Private chain-of-thought is never persisted. Event payloads are sanitized
metadata only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Union
import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import AgentEvent, AgentRun
from app.services.repositories import (
    AgentEventRepository,
    AgentRunRepository,
)

RunId = Union[UUID, str]


class TraceService:
    """Records agent execution runs and events."""

    EVENT_RUN_STARTED = "RUN_STARTED"
    EVENT_AGENT_STARTED = "AGENT_STARTED"
    EVENT_AGENT_THINKING = "AGENT_THINKING"
    EVENT_TOOL_STARTED = "TOOL_STARTED"
    EVENT_TOOL_COMPLETED = "TOOL_COMPLETED"
    EVENT_AGENT_COMPLETED = "AGENT_COMPLETED"
    EVENT_AGENT_FAILED = "AGENT_FAILED"
    EVENT_RUN_COMPLETED = "RUN_COMPLETED"
    EVENT_RUN_FAILED = "RUN_FAILED"

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.run_repo = AgentRunRepository(session)
        self.event_repo = AgentEventRepository(session)
        # Per-run sequence counters, keyed by run id (string form).
        self._run_sequences: dict[str, int] = {}

    def _run_id_str(self, run_id: RunId) -> str:
        return str(run_id)

    def _next_sequence(self, run_id: RunId) -> int:
        key = self._run_id_str(run_id)
        self._run_sequences.setdefault(key, 0)
        self._run_sequences[key] += 1
        return self._run_sequences[key]

    async def start_run(
        self,
        *,
        request_id: str,
        capability: str,
        profile_id: UUID | None = None,
        provider: str | None = None,
        model: str | None = None,
    ) -> AgentRun:
        run = AgentRun(
            request_id=request_id,
            capability=capability,
            profile_id=profile_id,
            status="PENDING",
            provider=provider,
            model=model,
        )
        run = await self.run_repo.add(run)
        self._run_sequences[self._run_id_str(run.id)] = 0
        await self.emit(
            run_id=run.id,
            event_type=self.EVENT_RUN_STARTED,
            message=f"Run started for capability '{capability}'.",
            payload={
                "capability": capability,
                "profile_id": str(profile_id) if profile_id else None,
            },
        )
        return run

    async def emit(
        self,
        *,
        run_id: RunId,
        event_type: str,
        agent_name: str | None = None,
        tool_name: str | None = None,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
        started_at=None,
        completed_at=None,
    ) -> AgentEvent:
        if isinstance(run_id, str):
            run_id = uuid.UUID(run_id)
        event = AgentEvent(
            agent_run_id=run_id,
            sequence=self._next_sequence(run_id),
            event_type=event_type,
            agent_name=agent_name,
            tool_name=tool_name,
            message=message,
            payload=payload,
            started_at=started_at,
            completed_at=completed_at,
        )
        return await self.event_repo.add(event)

    async def complete_run(
        self,
        run: AgentRun,
        *,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AgentRun:
        run.status = "COMPLETED"
        run.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()
        await self.emit(
            run_id=run.id,
            event_type=self.EVENT_RUN_COMPLETED,
            message=message or f"Run {run.id} completed.",
            payload=payload,
        )
        return run

    async def fail_run(
        self,
        run: AgentRun,
        *,
        error: str,
        message: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> AgentRun:
        run.status = "FAILED"
        run.error = error
        run.completed_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()
        await self.emit(
            run_id=run.id,
            event_type=self.EVENT_RUN_FAILED,
            agent_name=None,
            tool_name=None,
            message=message or f"Run {run.id} failed: {error}",
            payload={"error": error, **(payload or {})},
        )
        return run


__all__ = ["TraceService", "RunId"]
