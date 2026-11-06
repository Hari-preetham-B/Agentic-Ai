"""Career knowledge API routes.

Endpoints:
- GET /careers — list curated career profiles
- GET /careers/{slug} — get a career with skills, tools, projects, sources
- GET /careers/{slug}/requirements — get career requirements
- POST /careers/recommendations — rank careers against a profile
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.dependency import get_current_user
from app.core.auth.ownership import require_owned_profile
from app.core.auth.provider import AuthenticatedUser
from app.core.database import get_session
from app.services.career_fit_service import compute_career_fit
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.career_recommendation_service import (
    CareerRecommendationService,
)
from app.services.repositories import ProfileRepository
from app.services.skill_matching import compute_skill_match, skill_gap_priority
from app.schemas.career import (
    CareerListResponse,
    CareerRecommendationsRequest,
    CareerRecommendationsResponse,
    CareerRecommendationItem,
    CareerRequirementsResponse,
    CareerResponse,
)

router = APIRouter(tags=["careers"])


def get_knowledge_service(
    session: AsyncSession = Depends(get_session),
) -> CareerKnowledgeService:
    return CareerKnowledgeService(session)


def get_recommendation_service(
    session: AsyncSession = Depends(get_session),
) -> CareerRecommendationService:
    return CareerRecommendationService(session)


@router.get(
    "/careers",
    response_model=CareerListResponse,
    summary="List curated career profiles",
)
async def list_careers(
    service: CareerKnowledgeService = Depends(get_knowledge_service),
) -> CareerListResponse:
    careers = await service.list_careers()
    return CareerListResponse(careers=[CareerResponse(**c) for c in careers])


@router.get(
    "/careers/{slug}",
    response_model=CareerResponse,
    summary="Get a career profile with skills, tools, projects, and sources",
)
async def get_career(
    slug: str,
    service: CareerKnowledgeService = Depends(get_knowledge_service),
) -> CareerResponse:
    career = await service.get_career(slug)
    if career is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Career not found"
        )
    return CareerResponse(**career)


@router.get(
    "/careers/{slug}/requirements",
    response_model=CareerRequirementsResponse,
    summary="Get career requirements (skills, tools, projects, sources)",
)
async def get_career_requirements(
    slug: str,
    service: CareerKnowledgeService = Depends(get_knowledge_service),
) -> CareerRequirementsResponse:
    reqs = await service.get_career_requirements(slug)
    if reqs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Career not found"
        )
    return CareerRequirementsResponse(**reqs)


class CareerSkillMatchDetail(BaseModel):
    skill_name: str
    category: str | None = None
    importance: str
    required_level: str | None = None
    user_level: str | None = None
    status: str
    score: float
    reason: str
    priority: str


class CareerMatchResponse(BaseModel):
    career_id: str
    slug: str
    title: str
    fit_score: float
    fit_summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    matched_count: int = 0
    partial_count: int = 0
    missing_count: int = 0
    skills: list[CareerSkillMatchDetail] = Field(default_factory=list)
    methodology: str


@router.get(
    "/careers/{slug}/match",
    response_model=CareerMatchResponse,
    summary="Match a profile against a career deterministically",
)
async def match_career(
    slug: str,
    profile_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CareerMatchResponse:
    await require_owned_profile(session, profile_id, current_user.user_id)
    career_service = CareerKnowledgeService(session)
    career = await career_service.get_career(slug)
    if career is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Career not found"
        )

    profile_repo = ProfileRepository(session)
    profile = await profile_repo.get(UUID(profile_id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    profile_skills = [
        {
            "name": s.name,
            "proficiency": s.proficiency,
            "years_experience": (
                float(s.years_experience) if s.years_experience is not None else None
            ),
            "source": s.source,
        }
        for s in (profile.skills or [])
    ]

    match = compute_skill_match(
        career_id=career["id"],
        career_title=career["title"],
        career_skills=career.get("skills", []),
        profile_skills=profile_skills,
    )
    fit = compute_career_fit(
        career_id=career["id"],
        career_title=career["title"],
        match_result=match,
    )
    details = [
        CareerSkillMatchDetail(
            **{**row, "priority": skill_gap_priority(row["status"], row["importance"])}
        )
        for row in (match.missing + match.partial + match.matched)
    ]
    details.sort(
        key=lambda d: (
            {"P0": 0, "P1": 1, "P2": 2}[d.priority],
            {"CORE": 0, "IMPORTANT": 1, "SUPPORTING": 2}.get(d.importance, 3),
            d.skill_name,
        )
    )
    return CareerMatchResponse(
        career_id=career["id"],
        slug=career["slug"],
        title=career["title"],
        fit_score=fit.fit_score,
        fit_summary=fit.fit_summary,
        strengths=fit.strengths,
        gaps=fit.gaps,
        matched_count=len(match.matched),
        partial_count=len(match.partial),
        missing_count=len(match.missing),
        skills=details,
        methodology=match.methodology,
    )


@router.post(
    "/careers/recommendations",
    response_model=CareerRecommendationsResponse,
    summary="Get deterministic career recommendations for a profile",
)
async def career_recommendations(
    request: CareerRecommendationsRequest,
    service: CareerRecommendationService = Depends(get_recommendation_service),
    session: AsyncSession = Depends(get_session),
    current_user: AuthenticatedUser = Depends(get_current_user),
) -> CareerRecommendationsResponse:
    await require_owned_profile(session, request.profile_id, current_user.user_id)
    # Load profile skills from the database
    profile_repo = ProfileRepository(session)
    profile = await profile_repo.get(UUID(request.profile_id))
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )

    profile_skills = [
        {
            "name": s.name,
            "proficiency": s.proficiency,
            "years_experience": (
                float(s.years_experience) if s.years_experience is not None else None
            ),
            "source": s.source,
        }
        for s in (profile.skills or [])
    ]

    recs = await service.recommend(
        profile_skills=profile_skills,
        limit=request.limit,
    )
    return CareerRecommendationsResponse(
        recommendations=[CareerRecommendationItem(**r.model_dump()) for r in recs]
    )


__all__ = ["router"]
