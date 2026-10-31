"""CareerTwin unified intelligence API routes.

Endpoints:
- GET  /careertwin — unified CareerTwin state
- GET  /careertwin/insights — cross-system insights
- GET  /careertwin/conflicts — cross-system conflicts
- GET  /careertwin/readiness — career readiness
- GET  /careertwin/stale — stale derived state
- POST /careertwin/refresh — refresh stale derived state
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.schemas.careertwin import (
    CareerTwinConflictsResponse,
    CareerTwinInsightsResponse,
    CareerTwinReadinessResponse,
    CareerTwinRefreshRequest,
    CareerTwinRefreshResponse,
    CareerTwinStaleResponse,
    CareerTwinState,
)
from app.services.careertwin_service import (
    CareerReadinessService,
    CareerTwinReconciliationService,
    CareerTwinStateService,
)

router = APIRouter(tags=["careertwin"])


@router.get(
    "/careertwin",
    response_model=CareerTwinState,
    summary="Get unified CareerTwin state",
)
async def get_careertwin(
    profile_id: str,
    active_target_career: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> CareerTwinState:
    service = CareerTwinStateService(session)
    try:
        state = await service.get_state(
            profile_id=profile_id,
            active_target_career=active_target_career,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return state


@router.get(
    "/careertwin/insights",
    response_model=CareerTwinInsightsResponse,
    summary="Get cross-system insights",
)
async def get_careertwin_insights(
    profile_id: str,
    active_target_career: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> CareerTwinInsightsResponse:
    service = CareerTwinStateService(session)
    try:
        state = await service.get_state(
            profile_id=profile_id,
            active_target_career=active_target_career,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return CareerTwinInsightsResponse(insights=state.insights)


@router.get(
    "/careertwin/conflicts",
    response_model=CareerTwinConflictsResponse,
    summary="Get cross-system conflicts",
)
async def get_careertwin_conflicts(
    profile_id: str,
    active_target_career: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> CareerTwinConflictsResponse:
    service = CareerTwinStateService(session)
    try:
        state = await service.get_state(
            profile_id=profile_id,
            active_target_career=active_target_career,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return CareerTwinConflictsResponse(conflicts=state.conflicts)


@router.get(
    "/careertwin/readiness",
    response_model=CareerTwinReadinessResponse,
    summary="Get career readiness",
)
async def get_careertwin_readiness(
    profile_id: str,
    career_slug: str,
    session: AsyncSession = Depends(get_session),
) -> CareerTwinReadinessResponse:
    service = CareerReadinessService(session)
    try:
        result = await service.calculate(
            profile_id=profile_id,
            career_slug=career_slug,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return CareerTwinReadinessResponse(
        readiness_level=result["readiness_level"],
        readiness_score=result["readiness_score"],
        rationale=result["rationale"],
        blockers=result["blockers"],
    )


@router.get(
    "/careertwin/stale",
    response_model=CareerTwinStaleResponse,
    summary="Get stale derived state",
)
async def get_careertwin_stale(
    profile_id: str,
    active_target_career: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> CareerTwinStaleResponse:
    service = CareerTwinStateService(session)
    try:
        state = await service.get_state(
            profile_id=profile_id,
            active_target_career=active_target_career,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        )
    return CareerTwinStaleResponse(stale_components=state.stale_components)


@router.post(
    "/careertwin/refresh",
    response_model=CareerTwinRefreshResponse,
    summary="Refresh stale derived state",
)
async def refresh_careertwin(
    request: CareerTwinRefreshRequest,
    session: AsyncSession = Depends(get_session),
) -> CareerTwinRefreshResponse:
    service = CareerTwinReconciliationService(session)
    trigger = "manual"
    result = await service.execute_refresh(
        profile_id=request.profile_id,
        trigger=trigger,
        active_target_career=None,
    )
    return CareerTwinRefreshResponse(
        refreshed_components=result["refreshed_components"],
        unchanged_components=result["unchanged_components"],
        message=result["message"],
    )


__all__ = ["router"]
