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

from app.core.auth.dependency import get_current_user
from app.core.auth.ownership import (
    require_owned_agent_run,
    require_owned_profile,
)
from app.core.auth.provider import AuthenticatedUser
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
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AgentRunResponse:
    """Run a capability through the agent orchestrator.

    Example capability: ``profile_summary`` → Profile Agent → get_profile tool
    → FakeLLMProvider → typed ProfileSummary.
    """
    if request.profile_id:
        await require_owned_profile(
            session, request.profile_id, current_user.user_id
        )
    result = await orchestrator.run_capability(
        capability=request.capability,
        profile_id=request.profile_id,
        user_input=request.input,
    )
    return AgentRunResponse(**result)


class AgentRunSummary(BaseModel):
    id: str
    request_id: str
    capability: str
    status: str
    provider: str | None = None
    model: str | None = None
    error: str | None = None
    started_at: Any = None
    completed_at: Any = None


@router.get(
    "/agent-runs",
    response_model=list[AgentRunSummary],
    summary="List the current user's agent runs for a profile",
)
async def list_agent_runs(
    profile_id: str,
    limit: int = 20,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[AgentRunSummary]:
    from app.services.repositories import AgentRunRepository

    profile = await require_owned_profile(
        session, profile_id, current_user.user_id
    )
    run_repo = AgentRunRepository(session)
    runs = await run_repo.list_by_profile(profile.id, limit=max(1, min(limit, 100)))
    return [
        AgentRunSummary(
            id=str(r.id),
            request_id=r.request_id,
            capability=r.capability,
            status=r.status,
            provider=r.provider,
            model=r.model,
            error=r.error,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@router.get(
    "/agent-runs/{run_id}",
    response_model=AgentRunDetailResponse,
    summary="Get an agent run and its events",
)
async def get_agent_run(
    run_id: UUID,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> AgentRunDetailResponse:
    from app.services.repositories import AgentEventRepository

    event_repo = AgentEventRepository(session)
    run = await require_owned_agent_run(session, run_id, current_user.user_id)

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
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> list[AgentEventResponse]:
    from app.services.repositories import AgentEventRepository

    event_repo = AgentEventRepository(session)
    run = await require_owned_agent_run(session, run_id, current_user.user_id)

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
