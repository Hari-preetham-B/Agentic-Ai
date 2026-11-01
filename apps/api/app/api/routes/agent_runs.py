"""Agent run API routes.

Endpoints:
- POST   /agent-runs              — execute a capability
- GET    /agent-runs/{run_id}     — get run status and result
- GET    /agent-runs/{run_id}/events — get ordered execution events
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.llm import FakeLLMProvider
from app.services.orchestrator import AgentOrchestrator
from app.services.trace import TraceService
from app.workflows.agent_workflow import AgentWorkflow

router = APIRouter(tags=["agent-runs"])


def _create_orchestrator_llm_provider():
    """Create an LLM provider for the orchestrator.

    Uses the configured provider (e.g. Gemini) if available,
    falls back to FakeLLMProvider for development/testing.
    """
    try:
        from app.core.providers import create_llm_provider

        return create_llm_provider()
    except Exception:
        from app.core.llm import FakeLLMProvider

        return FakeLLMProvider()


def get_orchestrator(
    session: AsyncSession = Depends(get_session),
) -> AgentOrchestrator:
    return AgentOrchestrator(
        session=session,
        trace_service=TraceService(session),
        llm_provider=_create_orchestrator_llm_provider(),
        workflow=AgentWorkflow(),
    )


class AgentRunRequest(BaseModel):
    profile_id: str | None = Field(
        default=None, description="UUID of the profile to operate on."
    )
    capability: str = Field(
        ...,
        description=(
            "Capability to execute. Supported: profile_summary, career_analysis, "
            "skill_gap, learning_plan, interview, evidence_check."
        ),
    )
    input: str = Field(default="", description="User instruction for the agent.")


class AgentRunResponse(BaseModel):
    run_id: str | None = None
    status: str
    agent: str | None = None
    result: Any = None
    error: str | None = None


class AgentEventResponse(BaseModel):
    id: str
    sequence: int
    event_type: str
    agent_name: str | None = None
    tool_name: str | None = None
    message: str | None = None
    payload: Any = None
    started_at: Any = None
    completed_at: Any = None
    created_at: Any = None


class AgentRunDetailResponse(BaseModel):
    id: str
    request_id: str
    capability: str
    status: str
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    started_at: Any = None
    completed_at: Any = None
    events: list[AgentEventResponse] = []


@router.post(
    "/agent-runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Execute an agent capability",
)
async def create_agent_run(
    request: AgentRunRequest,
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
) -> AgentRunResponse:
    """Run a capability through the agent orchestrator.

    Example capability: ``profile_summary`` → Profile Agent → get_profile tool
    → FakeLLMProvider → typed ProfileSummary.
    """
    result = await orchestrator.run_capability(
        capability=request.capability,
        profile_id=request.profile_id,
        user_input=request.input,
    )
    return AgentRunResponse(**result)


@router.get(
    "/agent-runs/{run_id}",
    response_model=AgentRunDetailResponse,
    summary="Get an agent run and its events",
)
async def get_agent_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> AgentRunDetailResponse:
    from app.services.repositories import AgentEventRepository, AgentRunRepository

    run_repo = AgentRunRepository(session)
    event_repo = AgentEventRepository(session)

    run = await run_repo.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found"
        )

    events = await event_repo.list_for_run(run_id)
    return AgentRunDetailResponse(
        id=str(run.id),
        request_id=run.request_id,
        capability=run.capability,
        status=run.status,
        provider=run.provider,
        model=run.model,
        error=run.error,
        started_at=run.started_at,
        completed_at=run.completed_at,
        events=[
            AgentEventResponse(
                id=str(e.id),
                sequence=e.sequence,
                event_type=e.event_type,
                agent_name=e.agent_name,
                tool_name=e.tool_name,
                message=e.message,
                payload=e.payload,
                started_at=e.started_at,
                completed_at=e.completed_at,
                created_at=e.created_at,
            )
            for e in events
        ],
    )


@router.get(
    "/agent-runs/{run_id}/events",
    response_model=list[AgentEventResponse],
    summary="Get ordered execution events for a run",
)
async def get_agent_run_events(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[AgentEventResponse]:
    from app.services.repositories import AgentEventRepository, AgentRunRepository

    run_repo = AgentRunRepository(session)
    event_repo = AgentEventRepository(session)

    run = await run_repo.get(run_id)
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found"
        )

    events = await event_repo.list_for_run(run_id)
    return [
        AgentEventResponse(
            id=str(e.id),
            sequence=e.sequence,
            event_type=e.event_type,
            agent_name=e.agent_name,
            tool_name=e.tool_name,
            message=e.message,
            payload=e.payload,
            started_at=e.started_at,
            completed_at=e.completed_at,
            created_at=e.created_at,
        )
        for e in events
    ]


__all__ = ["router"]
