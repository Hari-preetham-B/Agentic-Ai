"""CareerTwin tools for agent execution.

Tools for unified CareerTwin intelligence operations.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.careertwin import (
    CareerTwinConflictsResponse,
    CareerTwinInsightsResponse,
    CareerTwinReadinessResponse,
    CareerTwinState,
    CareerTwinStaleResponse,
)
from app.services.careertwin_service import (
    CareerReadinessService,
    CareerTwinStateService,
)
from app.tools import Tool


# ---------------------------------------------------------------------------
# get_careertwin_state tool
# ---------------------------------------------------------------------------


class GetCareerTwinStateInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Profile ID.")
    active_target_career: str | None = Field(default=None)


class GetCareerTwinStateOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    state: dict[str, Any] = Field(default_factory=dict)


class GetCareerTwinStateTool(Tool[GetCareerTwinStateInput, GetCareerTwinStateOutput]):
    input_schema = GetCareerTwinStateInput
    output_schema = GetCareerTwinStateOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_careertwin_state",
            description="Retrieve the unified CareerTwin state for a profile.",
        )
        self._session = session

    async def _run(self, input_data: GetCareerTwinStateInput) -> dict[str, Any]:
        service = CareerTwinStateService(self._session)
        state = await service.get_state(
            profile_id=input_data.profile_id,
            active_target_career=input_data.active_target_career,
        )
        return {"state": state.model_dump()}


# ---------------------------------------------------------------------------
# calculate_career_readiness tool
# ---------------------------------------------------------------------------


class CalculateCareerReadinessInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Profile ID.")
    career_slug: str = Field(..., description="Career slug.")


class CalculateCareerReadinessOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    readiness_level: str
    readiness_score: float
    fit_score: float
    critical_missing: int
    dependency_blockers: int
    blockers: list[str] = Field(default_factory=list)
    rationale: str


class CalculateCareerReadinessTool(
    Tool[CalculateCareerReadinessInput, CalculateCareerReadinessOutput]
):
    input_schema = CalculateCareerReadinessInput
    output_schema = CalculateCareerReadinessOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="calculate_career_readiness",
            description="Calculate deterministic career readiness for a profile-career pair.",
        )
        self._session = session

    async def _run(self, input_data: CalculateCareerReadinessInput) -> dict[str, Any]:
        service = CareerReadinessService(self._session)
        result = await service.calculate(
            profile_id=input_data.profile_id,
            career_slug=input_data.career_slug,
        )
        return result


# ---------------------------------------------------------------------------
# get_careertwin_insights tool
# ---------------------------------------------------------------------------


class GetCareerTwinInsightsInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Profile ID.")
    active_target_career: str | None = Field(default=None)


class GetCareerTwinInsightsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    insights: list[dict] = Field(default_factory=list)


class GetCareerTwinInsightsTool(
    Tool[GetCareerTwinInsightsInput, GetCareerTwinInsightsOutput]
):
    input_schema = GetCareerTwinInsightsInput
    output_schema = GetCareerTwinInsightsOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_careertwin_insights",
            description="Get cross-system insights for a profile.",
        )
        self._session = session

    async def _run(self, input_data: GetCareerTwinInsightsInput) -> dict[str, Any]:
        state_service = CareerTwinStateService(self._session)
        state = await state_service.get_state(
            profile_id=input_data.profile_id,
            active_target_career=input_data.active_target_career,
        )
        return {"insights": [i.model_dump() for i in state.insights]}


# ---------------------------------------------------------------------------
# get_careertwin_conflicts tool
# ---------------------------------------------------------------------------


class GetCareerTwinConflictsInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Profile ID.")
    active_target_career: str | None = Field(default=None)


class GetCareerTwinConflictsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    conflicts: list[dict] = Field(default_factory=list)


class GetCareerTwinConflictsTool(
    Tool[GetCareerTwinConflictsInput, GetCareerTwinConflictsOutput]
):
    input_schema = GetCareerTwinConflictsInput
    output_schema = GetCareerTwinConflictsOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_careertwin_conflicts",
            description="Get cross-system conflicts for a profile.",
        )
        self._session = session

    async def _run(self, input_data: GetCareerTwinConflictsInput) -> dict[str, Any]:
        state_service = CareerTwinStateService(self._session)
        state = await state_service.get_state(
            profile_id=input_data.profile_id,
            active_target_career=input_data.active_target_career,
        )
        return {"conflicts": [c.model_dump() for c in state.conflicts]}


# ---------------------------------------------------------------------------
# get_stale_derived_state tool
# ---------------------------------------------------------------------------


class GetStaleDerivedStateInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Profile ID.")
    active_target_career: str | None = Field(default=None)


class GetStaleDerivedStateOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    stale_components: list[dict] = Field(default_factory=list)


class GetStaleDerivedStateTool(
    Tool[GetStaleDerivedStateInput, GetStaleDerivedStateOutput]
):
    input_schema = GetStaleDerivedStateInput
    output_schema = GetStaleDerivedStateOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_stale_derived_state",
            description="Get stale derived state components for a profile.",
        )
        self._session = session

    async def _run(self, input_data: GetStaleDerivedStateInput) -> dict[str, Any]:
        state_service = CareerTwinStateService(self._session)
        state = await state_service.get_state(
            profile_id=input_data.profile_id,
            active_target_career=input_data.active_target_career,
        )
        return {"stale_components": [s.model_dump() for s in state.stale_components]}


# ---------------------------------------------------------------------------
# refresh_careertwin_state tool
# ---------------------------------------------------------------------------


class RefreshCareerTwinStateInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Profile ID.")
    trigger: str = Field(default="manual", description="Refresh trigger.")


class RefreshCareerTwinStateOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    refreshed_components: list[str] = Field(default_factory=list)
    unchanged_components: list[str] = Field(default_factory=list)
    message: str


class RefreshCareerTwinStateTool(
    Tool[RefreshCareerTwinStateInput, RefreshCareerTwinStateOutput]
):
    input_schema = RefreshCareerTwinStateInput
    output_schema = RefreshCareerTwinStateOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="refresh_careertwin_state",
            description="Refresh stale derived state components.",
        )
        self._session = session

    async def _run(self, input_data: RefreshCareerTwinStateInput) -> dict[str, Any]:
        from app.services.careertwin_service import CareerTwinReconciliationService

        service = CareerTwinReconciliationService(self._session)
        plan = service.get_refresh_plan(trigger=input_data.trigger)
        return {
            "refreshed_components": plan,
            "unchanged_components": [],
            "message": f"Refresh plan generated for trigger: {input_data.trigger}",
        }


__all__ = [
    "GetCareerTwinStateInput",
    "GetCareerTwinStateOutput",
    "GetCareerTwinStateTool",
    "CalculateCareerReadinessInput",
    "CalculateCareerReadinessOutput",
    "CalculateCareerReadinessTool",
    "GetCareerTwinInsightsInput",
    "GetCareerTwinInsightsOutput",
    "GetCareerTwinInsightsTool",
    "GetCareerTwinConflictsInput",
    "GetCareerTwinConflictsOutput",
    "GetCareerTwinConflictsTool",
    "GetStaleDerivedStateInput",
    "GetStaleDerivedStateOutput",
    "GetStaleDerivedStateTool",
    "RefreshCareerTwinStateInput",
    "RefreshCareerTwinStateOutput",
    "RefreshCareerTwinStateTool",
    "build_get_careertwin_state_tool",
    "build_calculate_career_readiness_tool",
    "build_get_careertwin_insights_tool",
    "build_get_careertwin_conflicts_tool",
    "build_get_stale_derived_state_tool",
    "build_refresh_careertwin_state_tool",
]


def build_get_careertwin_state_tool(session: AsyncSession) -> GetCareerTwinStateTool:
    return GetCareerTwinStateTool(session)


def build_calculate_career_readiness_tool(session: AsyncSession) -> CalculateCareerReadinessTool:
    return CalculateCareerReadinessTool(session)


def build_get_careertwin_insights_tool(session: AsyncSession) -> GetCareerTwinInsightsTool:
    return GetCareerTwinInsightsTool(session)


def build_get_careertwin_conflicts_tool(session: AsyncSession) -> GetCareerTwinConflictsTool:
    return GetCareerTwinConflictsTool(session)


def build_get_stale_derived_state_tool(session: AsyncSession) -> GetStaleDerivedStateTool:
    return GetStaleDerivedStateTool(session)


def build_refresh_careertwin_state_tool(session: AsyncSession) -> RefreshCareerTwinStateTool:
    return RefreshCareerTwinStateTool(session)
