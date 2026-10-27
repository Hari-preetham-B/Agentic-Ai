"""Career tools for agent execution.

Tools are deterministic capabilities that agents can invoke. They use the
service/repository layer — never raw SQL or direct SQLAlchemy session
manipulation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.career_recommendation_service import CareerRecommendationService
from app.services.skill_matching import compute_skill_match
from app.tools import Tool


# ---------------------------------------------------------------------------
# get_career tool
# ---------------------------------------------------------------------------


class GetCareerInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str = Field(..., description="Career slug (e.g. 'software-engineer').")


class GetCareerOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    slug: str
    title: str
    domain: str
    summary: str | None = None
    description: str | None = None
    education_expectations: dict | None = None
    experience_expectations: dict | None = None
    skills: list[dict] = Field(default_factory=list)
    tools: list[dict] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)


class GetCareerTool(Tool[GetCareerInput, GetCareerOutput]):
    input_schema = GetCareerInput
    output_schema = GetCareerOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_career",
            description="Retrieve a curated career profile by slug, including skills, tools, projects, and sources.",
        )
        self._session = session

    async def _run(self, input_data: GetCareerInput) -> dict[str, Any]:
        service = CareerKnowledgeService(self._session)
        result = await service.get_career(input_data.slug)
        if result is None:
            raise ValueError(f"Career not found: {input_data.slug}")
        return result


# ---------------------------------------------------------------------------
# list_careers tool
# ---------------------------------------------------------------------------


class ListCareersInput(BaseModel):
    model_config = ConfigDict(frozen=True)


class ListCareersOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    careers: list[dict] = Field(default_factory=list)


class ListCareersTool(Tool[ListCareersInput, ListCareersOutput]):
    input_schema = ListCareersInput
    output_schema = ListCareersOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="list_careers",
            description="List all curated career profiles.",
        )
        self._session = session

    async def _run(self, input_data: ListCareersInput) -> dict[str, Any]:
        service = CareerKnowledgeService(self._session)
        careers = await service.list_careers()
        return {"careers": careers}


# ---------------------------------------------------------------------------
# get_career_requirements tool
# ---------------------------------------------------------------------------


class GetCareerRequirementsInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    slug: str = Field(..., description="Career slug.")


class GetCareerRequirementsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    career_id: str
    slug: str
    title: str
    domain: str
    skills: list[dict] = Field(default_factory=list)
    tools: list[dict] = Field(default_factory=list)
    projects: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)


class GetCareerRequirementsTool(Tool[GetCareerRequirementsInput, GetCareerRequirementsOutput]):
    input_schema = GetCareerRequirementsInput
    output_schema = GetCareerRequirementsOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_career_requirements",
            description="Retrieve career requirements (skills, tools, projects, sources) for a career slug.",
        )
        self._session = session

    async def _run(self, input_data: GetCareerRequirementsInput) -> dict[str, Any]:
        service = CareerKnowledgeService(self._session)
        result = await service.get_career_requirements(input_data.slug)
        if result is None:
            raise ValueError(f"Career requirements not found: {input_data.slug}")
        return result


# ---------------------------------------------------------------------------
# calculate_skill_match tool
# ---------------------------------------------------------------------------


class CalculateSkillMatchInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    career_id: str = Field(..., description="Career ID.")
    career_title: str = Field(..., description="Career title.")
    career_skills: list[dict] = Field(default_factory=list)
    profile_skills: list[dict] = Field(default_factory=list)


class CalculateSkillMatchOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    career_id: str
    career_title: str
    matched: list[dict] = Field(default_factory=list)
    partial: list[dict] = Field(default_factory=list)
    missing: list[dict] = Field(default_factory=list)
    overall_score: float
    methodology: str


class CalculateSkillMatchTool(Tool[CalculateSkillMatchInput, CalculateSkillMatchOutput]):
    input_schema = CalculateSkillMatchInput
    output_schema = CalculateSkillMatchOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="calculate_skill_match",
            description="Compute deterministic skill match between profile skills and career requirements.",
        )
        self._session = session

    async def _run(self, input_data: CalculateSkillMatchInput) -> dict[str, Any]:
        result = compute_skill_match(
            career_id=input_data.career_id,
            career_title=input_data.career_title,
            career_skills=input_data.career_skills,
            profile_skills=input_data.profile_skills,
        )
        return result.model_dump()


# ---------------------------------------------------------------------------
# get_career_recommendations tool
# ---------------------------------------------------------------------------


class GetCareerRecommendationsInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_skills: list[dict] = Field(default_factory=list)
    limit: int = Field(default=5, ge=1, le=10)


class GetCareerRecommendationsOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    recommendations: list[dict] = Field(default_factory=list)


class GetCareerRecommendationsTool(Tool[GetCareerRecommendationsInput, GetCareerRecommendationsOutput]):
    input_schema = GetCareerRecommendationsInput
    output_schema = GetCareerRecommendationsOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_career_recommendations",
            description="Rank careers against profile skills and return top recommendations.",
        )
        self._session = session

    async def _run(self, input_data: GetCareerRecommendationsInput) -> dict[str, Any]:
        service = CareerRecommendationService(self._session)
        recs = await service.recommend(
            profile_skills=input_data.profile_skills,
            limit=input_data.limit,
        )
        return {"recommendations": [r.model_dump() for r in recs]}


__all__ = [
    "GetCareerInput",
    "GetCareerOutput",
    "GetCareerTool",
    "ListCareersInput",
    "ListCareersOutput",
    "ListCareersTool",
    "GetCareerRequirementsInput",
    "GetCareerRequirementsOutput",
    "GetCareerRequirementsTool",
    "CalculateSkillMatchInput",
    "CalculateSkillMatchOutput",
    "CalculateSkillMatchTool",
    "GetCareerRecommendationsInput",
    "GetCareerRecommendationsOutput",
    "GetCareerRecommendationsTool",
    "build_get_career_tool",
    "build_list_careers_tool",
    "build_get_career_requirements_tool",
    "build_calculate_skill_match_tool",
    "build_get_career_recommendations_tool",
]


def build_get_career_tool(session: AsyncSession) -> GetCareerTool:
    return GetCareerTool(session)


def build_list_careers_tool(session: AsyncSession) -> ListCareersTool:
    return ListCareersTool(session)


def build_get_career_requirements_tool(session: AsyncSession) -> GetCareerRequirementsTool:
    return GetCareerRequirementsTool(session)


def build_calculate_skill_match_tool(session: AsyncSession) -> CalculateSkillMatchTool:
    return CalculateSkillMatchTool(session)


def build_get_career_recommendations_tool(session: AsyncSession) -> GetCareerRecommendationsTool:
    return GetCareerRecommendationsTool(session)
