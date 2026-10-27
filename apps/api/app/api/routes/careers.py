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

from app.core.database import get_session
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.career_recommendation_service import (
    CareerRecommendationService,
)
from app.services.repositories import ProfileRepository
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


@router.post(
    "/careers/recommendations",
    response_model=CareerRecommendationsResponse,
    summary="Get deterministic career recommendations for a profile",
)
async def career_recommendations(
    request: CareerRecommendationsRequest,
    service: CareerRecommendationService = Depends(get_recommendation_service),
    session: AsyncSession = Depends(get_session),
) -> CareerRecommendationsResponse:
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
