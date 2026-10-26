"""Profile retrieval tool.

A deterministic tool that retrieves the structured CareerTwin profile from
PostgreSQL. It never calls an LLM. Database access goes through the repository
layer — the tool never executes SQL directly.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.repositories import ProfileRepository
from app.tools import Tool


class GetProfileInput(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_id: str = Field(..., description="UUID of the profile to retrieve.")


class GetProfileOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    full_name: str | None = None
    headline: str | None = None
    email: str | None = None
    location: str | None = None
    summary: str | None = None
    profile_status: str
    education: list[dict[str, Any]] = Field(default_factory=list)
    skills: list[dict[str, Any]] = Field(default_factory=list)
    projects: list[dict[str, Any]] = Field(default_factory=list)
    experience: list[dict[str, Any]] = Field(default_factory=list)
    career_goals: list[dict[str, Any]] = Field(default_factory=list)


class GetProfileTool(Tool[GetProfileInput, GetProfileOutput]):
    """Retrieves a structured CareerTwin profile from the database."""

    input_schema = GetProfileInput
    output_schema = GetProfileOutput

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(
            name="get_profile",
            description="Retrieve the structured CareerTwin profile for a given profile ID.",
        )
        self._session = session
        self._repo = ProfileRepository(session)

    async def _run(self, input_data: GetProfileInput) -> dict[str, Any]:
        try:
            profile_id = UUID(input_data.profile_id)
        except ValueError as exc:
            raise ValueError(f"Invalid profile_id: {input_data.profile_id}") from exc

        profile = await self._repo.get(profile_id)
        if profile is None:
            raise ValueError(f"Profile not found: {input_data.profile_id}")

        return {
            "id": str(profile.id),
            "full_name": profile.full_name,
            "headline": profile.headline,
            "email": profile.email,
            "location": profile.location,
            "summary": profile.summary,
            "profile_status": profile.profile_status,
            "education": [
                {
                    "id": str(e.id),
                    "institution": e.institution,
                    "degree": e.degree,
                    "field_of_study": e.field_of_study,
                    "start_date": e.start_date.isoformat() if e.start_date else None,
                    "end_date": e.end_date.isoformat() if e.end_date else None,
                    "description": e.description,
                }
                for e in (profile.education or [])
            ],
            "skills": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "category": s.category,
                    "proficiency": s.proficiency,
                    "years_experience": (
                        float(s.years_experience) if s.years_experience is not None else None
                    ),
                    "source": s.source,
                }
                for s in (profile.skills or [])
            ],
            "projects": [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "description": p.description,
                    "technologies": p.technologies,
                    "role": p.role,
                    "outcomes": p.outcomes,
                    "start_date": p.start_date.isoformat() if p.start_date else None,
                    "end_date": p.end_date.isoformat() if p.end_date else None,
                    "source": p.source,
                }
                for p in (profile.projects or [])
            ],
            "experience": [
                {
                    "id": str(x.id),
                    "organization": x.organization,
                    "role": x.role,
                    "description": x.description,
                    "achievements": x.achievements,
                    "start_date": x.start_date.isoformat() if x.start_date else None,
                    "end_date": x.end_date.isoformat() if x.end_date else None,
                    "is_current": x.is_current,
                    "source": x.source,
                }
                for x in (profile.experience or [])
            ],
            "career_goals": [
                {
                    "id": str(g.id),
                    "target_role": g.target_role,
                    "target_industry": g.target_industry,
                    "target_domain": g.target_domain,
                    "goal_description": g.goal_description,
                    "priority": g.priority,
                }
                for g in (profile.career_goals or [])
            ],
        }


def build_get_profile_tool(session: AsyncSession) -> GetProfileTool:
    """Build a request-scoped GetProfileTool bound to the given session."""
    return GetProfileTool(session)

__all__ = [
    "GetProfileInput",
    "GetProfileOutput",
    "GetProfileTool",
    "build_get_profile_tool",
]
