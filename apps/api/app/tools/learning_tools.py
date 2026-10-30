"""Learning tools for agent execution.

Tools for learning intelligence and roadmap operations. They use the
service/repository layer — never raw SQL or direct SQLAlchemy session
manipulation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.learning_roadmap_service import LearningRoadmapService
from app.services.skill_dependency_service import SkillDependencyService
from app.tools import Tool


# ---------------------------------------------------------------------------
# get_learning_resources tool
# ---------------------------------------------------------------------------


class GetLearningResourcesInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_name: str | None = Field(default=None)
    resource_type: str | None = Field(default=None)


class GetLearningResourcesOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    resources: list[dict] = Field(default_factory=list)


class GetLearningResourcesTool(Tool[GetLearningResourcesInput, GetLearningResourcesOutput]):
    input_schema = GetLearningResourcesInput
    output_schema = GetLearningResourcesOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_learning_resources",
            description="Retrieve learning resources, optionally filtered by skill or type.",
        )
        self._session = session

    async def _run(self, input_data: GetLearningResourcesInput) -> dict[str, Any]:
        from sqlalchemy import select
        from app.models.learning import LearningResource, LearningResourceSkill

        if input_data.skill_name:
            stmt = (
                select(LearningResource)
                .join(
                    LearningResourceSkill,
                    LearningResource.id == LearningResourceSkill.resource_id,
                )
                .where(LearningResourceSkill.skill_name == input_data.skill_name)
            )
        else:
            stmt = select(LearningResource)

        if input_data.resource_type:
            stmt = stmt.where(LearningResource.resource_type == input_data.resource_type)

        result = await self._session.execute(stmt)
        resources = result.scalars().all()

        return {
            "resources": [
                {
                    "id": str(r.id),
                    "title": r.title,
                    "provider": r.provider,
                    "resource_type": r.resource_type,
                    "url": r.url,
                    "description": r.description,
                    "difficulty": r.difficulty,
                    "estimated_hours": r.estimated_hours,
                }
                for r in resources
            ]
        }


# ---------------------------------------------------------------------------
# get_skill_dependencies tool
# ---------------------------------------------------------------------------


class GetSkillDependenciesInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_name: str = Field(..., description="Skill name to get dependencies for.")


class GetSkillDependenciesOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill: str
    dependencies: list[dict] = Field(default_factory=list)
    all_dependencies: list[dict] = Field(default_factory=list)


class GetSkillDependenciesTool(
    Tool[GetSkillDependenciesInput, GetSkillDependenciesOutput]
):
    input_schema = GetSkillDependenciesInput
    output_schema = GetSkillDependenciesOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_skill_dependencies",
            description="Retrieve skill dependencies (prerequisites) for a skill.",
        )
        self._session = session

    async def _run(self, input_data: GetSkillDependenciesInput) -> dict[str, Any]:
        service = SkillDependencyService(self._session)
        deps = await service.get_dependencies(input_data.skill_name)
        all_deps = await service.get_all_dependencies()
        return {
            "skill": input_data.skill_name,
            "dependencies": deps,
            "all_dependencies": all_deps,
        }


# ---------------------------------------------------------------------------
# calculate_learning_priority tool
# ---------------------------------------------------------------------------


class CalculateLearningPriorityInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill_name: str = Field(..., description="Skill name.")
    importance: str = Field(default="SUPPORTING")
    current_proficiency: str | None = Field(default=None)
    gap_severity: float = Field(default=1.0, ge=0.0, le=1.0)
    downstream_count: int = Field(default=0, ge=0)
    total_skills: int = Field(default=1, ge=1)
    estimated_hours: float | None = Field(default=None)


class CalculateLearningPriorityOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    skill: str
    priority: str


class CalculateLearningPriorityTool(
    Tool[CalculateLearningPriorityInput, CalculateLearningPriorityOutput]
):
    input_schema = CalculateLearningPriorityInput
    output_schema = CalculateLearningPriorityOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="calculate_learning_priority",
            description="Calculate deterministic priority for a learning skill.",
        )
        self._session = session

    async def _run(self, input_data: CalculateLearningPriorityInput) -> dict[str, Any]:
        from app.services.roadmap_priority_engine import RoadmapPriorityEngine

        engine = RoadmapPriorityEngine()
        priority = engine.calculate_priority(
            skill_name=input_data.skill_name,
            importance=input_data.importance,
            current_proficiency=input_data.current_proficiency,
            gap_severity=input_data.gap_severity,
            downstream_count=input_data.downstream_count,
            total_skills=input_data.total_skills,
            estimated_hours=input_data.estimated_hours,
        )
        return {"skill": input_data.skill_name, "priority": priority}


# ---------------------------------------------------------------------------
# generate_learning_roadmap tool
# ---------------------------------------------------------------------------


class GenerateLearningRoadmapInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="Profile ID.")
    career_slug: str = Field(..., description="Target career slug.")
    profile_skills: list[dict] = Field(default_factory=list)


class GenerateLearningRoadmapOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    roadmap_id: str
    profile_id: str
    career_id: str
    career_title: str
    items: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class GenerateLearningRoadmapTool(
    Tool[GenerateLearningRoadmapInput, GenerateLearningRoadmapOutput]
):
    input_schema = GenerateLearningRoadmapInput
    output_schema = GenerateLearningRoadmapOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="generate_learning_roadmap",
            description="Generate a personalized learning roadmap.",
        )
        self._session = session

    async def _run(self, input_data: GenerateLearningRoadmapInput) -> dict[str, Any]:
        service = LearningRoadmapService(self._session)
        result = await service.generate_roadmap(
            profile_id=input_data.profile_id,
            career_slug=input_data.career_slug,
            profile_skills=input_data.profile_skills,
        )
        return result


# ---------------------------------------------------------------------------
# get_roadmap tool
# ---------------------------------------------------------------------------


class GetRoadmapInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    roadmap_id: str = Field(..., description="Roadmap ID.")


class GetRoadmapOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    roadmap_id: str
    profile_id: str
    career_id: str | None = None
    status: str
    generated_at: str
    items: list[dict] = Field(default_factory=list)


class GetRoadmapTool(Tool[GetRoadmapInput, GetRoadmapOutput]):
    input_schema = GetRoadmapInput
    output_schema = GetRoadmapOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_roadmap",
            description="Retrieve a roadmap by ID.",
        )
        self._session = session

    async def _run(self, input_data: GetRoadmapInput) -> dict[str, Any]:
        service = LearningRoadmapService(self._session)
        result = await service.get_roadmap(input_data.roadmap_id)
        if result is None:
            raise ValueError(f"Roadmap not found: {input_data.roadmap_id}")
        return result


__all__ = [
    "GetLearningResourcesInput",
    "GetLearningResourcesOutput",
    "GetLearningResourcesTool",
    "GetSkillDependenciesInput",
    "GetSkillDependenciesOutput",
    "GetSkillDependenciesTool",
    "CalculateLearningPriorityInput",
    "CalculateLearningPriorityOutput",
    "CalculateLearningPriorityTool",
    "GenerateLearningRoadmapInput",
    "GenerateLearningRoadmapOutput",
    "GenerateLearningRoadmapTool",
    "GetRoadmapInput",
    "GetRoadmapOutput",
    "GetRoadmapTool",
    "build_get_learning_resources_tool",
    "build_get_skill_dependencies_tool",
    "build_calculate_learning_priority_tool",
    "build_generate_learning_roadmap_tool",
    "build_get_roadmap_tool",
]


def build_get_learning_resources_tool(session: AsyncSession) -> GetLearningResourcesTool:
    return GetLearningResourcesTool(session)


def build_get_skill_dependencies_tool(session: AsyncSession) -> GetSkillDependenciesTool:
    return GetSkillDependenciesTool(session)


def build_calculate_learning_priority_tool(session: AsyncSession) -> CalculateLearningPriorityTool:
    return CalculateLearningPriorityTool(session)


def build_generate_learning_roadmap_tool(session: AsyncSession) -> GenerateLearningRoadmapTool:
    return GenerateLearningRoadmapTool(session)


def build_get_roadmap_tool(session: AsyncSession) -> GetRoadmapTool:
    return GetRoadmapTool(session)
