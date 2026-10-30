"""Learning intelligence API routes.

Endpoints:
- GET /learning/resources — list learning resources
- GET /learning/dependencies/{skill_id} — get skill dependencies
- POST /learning/roadmaps — generate a learning roadmap
- GET /learning/roadmaps/{roadmap_id} — get a roadmap
- POST /learning/roadmaps/{roadmap_id}/regenerate — regenerate a roadmap
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.services.learning_roadmap_service import LearningRoadmapService
from app.services.skill_dependency_service import SkillDependencyService
from app.services.repositories import ProfileRepository

router = APIRouter(tags=["learning"])


# ---------------------------------------------------------------------------
# Learning resources
# ---------------------------------------------------------------------------


class LearningResourceResponse(BaseModel):
    id: str
    title: str
    provider: str
    resource_type: str
    url: str | None = None
    description: str | None = None
    difficulty: str | None = None
    estimated_hours: float | None = None


class LearningResourcesResponse(BaseModel):
    resources: list[LearningResourceResponse]


@router.get(
    "/learning/resources",
    response_model=LearningResourcesResponse,
    summary="List learning resources",
)
async def list_learning_resources(
    session: AsyncSession = Depends(get_session),
) -> LearningResourcesResponse:
    from sqlalchemy import select
    from app.models.learning import LearningResource

    result = await session.execute(select(LearningResource))
    resources = result.scalars().all()
    return LearningResourcesResponse(
        resources=[
            LearningResourceResponse(
                id=str(r.id),
                title=r.title,
                provider=r.provider,
                resource_type=r.resource_type,
                url=r.url,
                description=r.description,
                difficulty=r.difficulty,
                estimated_hours=r.estimated_hours,
            )
            for r in resources
        ]
    )


# ---------------------------------------------------------------------------
# Skill dependencies
# ---------------------------------------------------------------------------


class SkillDependenciesResponse(BaseModel):
    skill: str
    dependencies: list[dict]
    all_dependencies: list[dict]


@router.get(
    "/learning/dependencies/{skill_name}",
    response_model=SkillDependenciesResponse,
    summary="Get skill dependencies for a skill",
)
async def get_skill_dependencies(
    skill_name: str,
    session: AsyncSession = Depends(get_session),
) -> SkillDependenciesResponse:
    service = SkillDependencyService(session)
    deps = await service.get_dependencies(skill_name)
    all_deps = await service.get_all_dependencies()
    return SkillDependenciesResponse(
        skill=skill_name,
        dependencies=deps,
        all_dependencies=all_deps,
    )


# ---------------------------------------------------------------------------
# Roadmap generation
# ---------------------------------------------------------------------------


class GenerateRoadmapRequest(BaseModel):
    profile_id: str = Field(..., description="Profile ID.")
    career_slug: str = Field(..., description="Target career slug.")
    profile_skills: list[dict] = Field(default_factory=list)


class RoadmapResponse(BaseModel):
    roadmap_id: str
    profile_id: str
    career_id: str | None = None
    career_title: str | None = None
    status: str
    generated_at: str
    items: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


@router.post(
    "/learning/roadmaps",
    response_model=RoadmapResponse,
    summary="Generate a learning roadmap",
)
async def generate_roadmap(
    request: GenerateRoadmapRequest,
    session: AsyncSession = Depends(get_session),
) -> RoadmapResponse:
    # Load profile skills if not provided
    profile_skills = request.profile_skills
    if not profile_skills:
        profile_repo = ProfileRepository(session)
        profile = await profile_repo.get(UUID(request.profile_id))
        if profile is not None:
            profile_skills = [
                {
                    "name": s.name,
                    "proficiency": s.proficiency,
                    "years_experience": (
                        float(s.years_experience)
                        if s.years_experience is not None
                        else None
                    ),
                    "source": s.source,
                }
                for s in (profile.skills or [])
            ]

    service = LearningRoadmapService(session)
    result = await service.generate_roadmap(
        profile_id=request.profile_id,
        career_slug=request.career_slug,
        profile_skills=profile_skills,
    )

    # Get the full roadmap
    roadmap = await service.get_roadmap(result["roadmap_id"])
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found after generation",
        )

    return RoadmapResponse(
        roadmap_id=roadmap["roadmap_id"],
        profile_id=roadmap["profile_id"],
        career_id=roadmap["career_id"],
        career_title=result.get("career_title"),
        status=roadmap["status"],
        generated_at=roadmap["generated_at"],
        items=roadmap["items"],
        summary=result.get("summary", {}),
    )


@router.get(
    "/learning/roadmaps/{roadmap_id}",
    response_model=RoadmapResponse,
    summary="Get a roadmap by ID",
)
async def get_roadmap(
    roadmap_id: str,
    session: AsyncSession = Depends(get_session),
) -> RoadmapResponse:
    service = LearningRoadmapService(session)
    roadmap = await service.get_roadmap(roadmap_id)
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found",
        )
    return RoadmapResponse(
        roadmap_id=roadmap["roadmap_id"],
        profile_id=roadmap["profile_id"],
        career_id=roadmap["career_id"],
        status=roadmap["status"],
        generated_at=roadmap["generated_at"],
        items=roadmap["items"],
        summary={},
    )


@router.post(
    "/learning/roadmaps/{roadmap_id}/regenerate",
    response_model=RoadmapResponse,
    summary="Regenerate a roadmap",
)
async def regenerate_roadmap(
    roadmap_id: str,
    request: GenerateRoadmapRequest,
    session: AsyncSession = Depends(get_session),
) -> RoadmapResponse:
    service = LearningRoadmapService(session)

    profile_skills = request.profile_skills
    if not profile_skills:
        profile_repo = ProfileRepository(session)
        profile = await profile_repo.get(UUID(request.profile_id))
        if profile is not None:
            profile_skills = [
                {
                    "name": s.name,
                    "proficiency": s.proficiency,
                    "years_experience": (
                        float(s.years_experience)
                        if s.years_experience is not None
                        else None
                    ),
                    "source": s.source,
                }
                for s in (profile.skills or [])
            ]

    result = await service.regenerate_roadmap(
        roadmap_id=roadmap_id,
        profile_id=request.profile_id,
        career_slug=request.career_slug,
        profile_skills=profile_skills,
    )

    roadmap = await service.get_roadmap(result["roadmap_id"])
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Roadmap not found after regeneration",
        )

    return RoadmapResponse(
        roadmap_id=roadmap["roadmap_id"],
        profile_id=roadmap["profile_id"],
        career_id=roadmap["career_id"],
        career_title=result.get("career_title"),
        status=roadmap["status"],
        generated_at=roadmap["generated_at"],
        items=roadmap["items"],
        summary=result.get("summary", {}),
    )


__all__ = ["router"]
