"""Tests for career recommendation service."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_engine_for_testing
from app.models.career import Career, CareerSkill
from app.models.profile import Profile, Skill
from app.services.career_recommendation_service import CareerRecommendationService


from app.core.database import set_engine_for_testing
from app.models.career import Career, CareerSkill
from app.models.profile import Profile, Skill
from app.services.career_recommendation_service import CareerRecommendationService
from sqlalchemy import delete


async def _clean_careers(session: AsyncSession) -> None:
    """Delete all career data to ensure test isolation."""
    await session.execute(delete(Career))
    await session.commit()


@pytest.mark.asyncio
async def test_recommendations_ranked(session: AsyncSession) -> None:
    """Test that recommendations are ranked by fit score."""
    await _clean_careers(session)
    # Seed two careers: one matching profile skills well, one poorly
    career_good_id = uuid.uuid4()
    career_good = Career(
        id=career_good_id,
        slug="good-match",
        title="Good Match Career",
        domain="Test",
        summary="Good match",
        description="Good match description.",
    )
    session.add(career_good)
    session.add(
        CareerSkill(
            career_id=career_good_id,
            skill_name="Python",
            category="Programming Language",
            importance="CORE",
            minimum_level="INTERMEDIATE",
        )
    )

    career_bad_id = uuid.uuid4()
    career_bad = Career(
        id=career_bad_id,
        slug="bad-match",
        title="Bad Match Career",
        domain="Test",
        summary="Bad match",
        description="Bad match description.",
    )
    session.add(career_bad)
    session.add(
        CareerSkill(
            career_id=career_bad_id,
            skill_name="ObscureSkill",
            category="Test",
            importance="CORE",
            minimum_level="EXPERT",
        )
    )

    await session.commit()

    service = CareerRecommendationService(session)
    recs = await service.recommend(
        profile_skills=[
            {"name": "Python", "proficiency": "INTERMEDIATE", "years_experience": 3.0, "source": "USER_CONFIRMED"},
        ],
        limit=5,
    )

    assert len(recs) == 2
    assert recs[0].career_title == "Good Match Career"
    assert recs[0].fit_score > recs[1].fit_score


@pytest.mark.asyncio
async def test_recommendations_limit(session: AsyncSession) -> None:
    """Test that limit is respected."""
    # Seed 3 careers
    for i in range(3):
        career_id = uuid.uuid4()
        session.add(
            Career(
                id=career_id,
                slug=f"career-{i}",
                title=f"Career {i}",
                domain="Test",
                summary=f"Career {i}",
                description=f"Career {i} description.",
            )
        )
        session.add(
            CareerSkill(
                career_id=career_id,
                skill_name="Python",
                category="Programming Language",
                importance="CORE",
                minimum_level="INTERMEDIATE",
            )
        )
    await session.commit()

    service = CareerRecommendationService(session)
    recs = await service.recommend(
        profile_skills=[
            {"name": "Python", "proficiency": "INTERMEDIATE", "years_experience": 3.0, "source": "USER_CONFIRMED"},
        ],
        limit=2,
    )

    assert len(recs) == 2


@pytest.mark.asyncio
async def test_recommendations_no_profile_skills(session: AsyncSession) -> None:
    """Test recommendations with no profile skills."""
    await _clean_careers(session)
    career_id = uuid.uuid4()
    session.add(
        Career(
            id=career_id,
            slug=f"no-skills-career-{uuid.uuid4().hex[:8]}",
            title="Test Career",
            domain="Test",
            summary="Test",
            description="Test description.",
        )
    )
    session.add(
        CareerSkill(
            career_id=career_id,
            skill_name="Python",
            category="Programming Language",
            importance="CORE",
            minimum_level="INTERMEDIATE",
        )
    )
    await session.commit()

    service = CareerRecommendationService(session)
    recs = await service.recommend(
        profile_skills=[],
        limit=5,
    )

    # Find our seeded career in the results
    our_recs = [r for r in recs if r.career_id == str(career_id)]
    assert len(our_recs) == 1
    assert our_recs[0].fit_score == 0.0


@pytest.mark.asyncio
async def test_recommendation_has_reason(session: AsyncSession) -> None:
    """Test that recommendations have a reason."""
    await _clean_careers(session)
    career_id = uuid.uuid4()
    session.add(
        Career(
            id=career_id,
            slug=f"reason-career-{uuid.uuid4().hex[:8]}",
            title="Test Career",
            domain="Test",
            summary="Test",
            description="Test description.",
        )
    )
    session.add(
        CareerSkill(
            career_id=career_id,
            skill_name="Python",
            category="Programming Language",
            importance="CORE",
            minimum_level="INTERMEDIATE",
        )
    )
    await session.commit()

    service = CareerRecommendationService(session)
    recs = await service.recommend(
        profile_skills=[
            {"name": "Python", "proficiency": "INTERMEDIATE", "years_experience": 3.0, "source": "USER_CONFIRMED"},
        ],
        limit=1,
    )

    # Find our seeded career in the results
    our_recs = [r for r in recs if r.career_id == str(career_id)]
    assert len(our_recs) == 1
    assert our_recs[0].reason is not None
    assert len(our_recs[0].reason) > 0


__all__ = [
    "test_recommendations_ranked",
    "test_recommendations_limit",
    "test_recommendations_no_profile_skills",
    "test_recommendation_has_reason",
]
