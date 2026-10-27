"""Deterministic career recommendation service.

Ranks careers against a confirmed profile using the SkillMatchingEngine.
No LLM is involved in ranking — the LLM may later explain why a career
ranked highly.
"""

from __future__ import annotations

from typing import Any

from app.models.career import Career, CareerSkill
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.skill_matching import compute_skill_match
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class CareerRecommendation:
    """A single career recommendation result."""

    def __init__(
        self,
        *,
        career_id: str,
        career_title: str,
        career_domain: str,
        fit_score: float,
        matched_core_skills: list[str],
        top_gaps: list[str],
        reason: str,
    ) -> None:
        self.career_id = career_id
        self.career_title = career_title
        self.career_domain = career_domain
        self.fit_score = fit_score
        self.matched_core_skills = matched_core_skills
        self.top_gaps = top_gaps
        self.reason = reason

    def model_dump(self) -> dict:
        return {
            "career_id": self.career_id,
            "career_title": self.career_title,
            "career_domain": self.career_domain,
            "fit_score": round(self.fit_score, 4),
            "matched_core_skills": self.matched_core_skills,
            "top_gaps": self.top_gaps,
            "reason": self.reason,
        }


class CareerRecommendationService:
    """Service for generating deterministic career recommendations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        from app.services.repositories import CareerRepository

        self.repo = CareerRepository(session)

    async def recommend(
        self,
        *,
        profile_skills: list[dict],
        limit: int = 5,
    ) -> list[CareerRecommendation]:
        """Rank all careers against profile skills.

        Args:
            profile_skills: List of dicts with keys name, proficiency,
                years_experience, source.
            limit: Maximum number of recommendations to return.

        Returns:
            List of CareerRecommendation ranked by fit score descending.
        """
        careers = await self.repo.list_careers()
        results: list[CareerRecommendation] = []

        for career in careers:
            skills = await self.repo.get_skills(career.id)
            career_skills = [
                {
                    "skill_name": s.skill_name,
                    "category": s.category,
                    "importance": s.importance,
                    "minimum_level": s.minimum_level,
                    "description": s.description,
                }
                for s in skills
            ]

            match = compute_skill_match(
                career_id=str(career.id),
                career_title=career.title,
                career_skills=career_skills,
                profile_skills=profile_skills,
            )

            matched_core = [
                m["skill_name"]
                for m in match.matched
                if m.get("importance") == "CORE"
            ]
            top_gaps = [
                m["skill_name"]
                for m in match.missing
                if m.get("importance") in ("CORE", "IMPORTANT")
            ][:5]

            reason = (
                f"{match.overall_score:.0%} skill alignment "
                f"({len(matched_core)} core skills matched)."
            )

            results.append(
                CareerRecommendation(
                    career_id=str(career.id),
                    career_title=career.title,
                    career_domain=career.domain,
                    fit_score=match.overall_score,
                    matched_core_skills=matched_core,
                    top_gaps=top_gaps,
                    reason=reason,
                )
            )

        # Rank by fit score descending
        results.sort(key=lambda r: r.fit_score, reverse=True)
        return results[:limit]
