"""Career knowledge service.

Application-level operations over curated career data. Agents and routes
access career data through this service (via repositories), never through
raw SQL or direct SQLAlchemy session manipulation.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from app.models.career import Career, CareerProject, CareerSkill, CareerSource, CareerTool
from app.services.repositories import CareerRepository


class CareerKnowledgeService:
    """Service for career knowledge retrieval."""

    def __init__(self, session) -> None:
        self.session = session
        self.repo = CareerRepository(session)

    async def list_careers(self) -> list[dict]:
        """Return all careers with their skills (tools/projects/sources omitted).

        Skills are included so list views can show each role's core skills
        without an extra request per career.
        """
        careers = await self.repo.list_careers()
        result: list[dict] = []
        for c in careers:
            skills = await self.repo.get_skills(c.id)
            result.append(
                {
                    "id": str(c.id),
                    "slug": c.slug,
                    "title": c.title,
                    "domain": c.domain,
                    "summary": c.summary,
                    "description": c.description,
                    "skills": [
                        {
                            "skill_name": s.skill_name,
                            "category": s.category,
                            "importance": s.importance,
                            "minimum_level": s.minimum_level,
                            "description": s.description,
                        }
                        for s in skills
                    ],
                }
            )
        return result

    async def get_career(self, slug: str) -> dict | None:
        """Return a career with its skills, tools, projects, and sources."""
        career = await self.repo.get_by_slug(slug)
        if career is None:
            return None

        skills = await self.repo.get_skills(career.id)
        tools = await self.repo.get_tools(career.id)
        projects = await self.repo.get_projects(career.id)
        sources = await self.repo.get_sources(career.id)

        return {
            "id": str(career.id),
            "slug": career.slug,
            "title": career.title,
            "domain": career.domain,
            "summary": career.summary,
            "description": career.description,
            "education_expectations": career.education_expectations,
            "experience_expectations": career.experience_expectations,
            "skills": [
                {
                    "skill_name": s.skill_name,
                    "category": s.category,
                    "importance": s.importance,
                    "minimum_level": s.minimum_level,
                    "description": s.description,
                }
                for s in skills
            ],
            "tools": [
                {
                    "tool_name": t.tool_name,
                    "category": t.category,
                    "importance": t.importance,
                }
                for t in tools
            ],
            "projects": [
                {
                    "project_type": p.project_type,
                    "description": p.description,
                    "skills_demonstrated": p.skills_demonstrated,
                    "difficulty": p.difficulty,
                }
                for p in projects
            ],
            "sources": [
                {
                    "title": src.title,
                    "publisher": src.publisher,
                    "url": src.url,
                    "source_type": src.source_type,
                    "published_at": src.published_at.isoformat() if src.published_at else None,
                    "reliability": src.reliability,
                }
                for src in sources
            ],
        }

    async def get_career_requirements(self, slug: str) -> dict | None:
        """Return career requirements (skills, tools, projects, sources) for a career."""
        detail = await self.get_career(slug)
        if detail is None:
            return None
        return {
            "career_id": detail["id"],
            "slug": detail["slug"],
            "title": detail["title"],
            "domain": detail["domain"],
            "skills": detail["skills"],
            "tools": detail["tools"],
            "projects": detail["projects"],
            "sources": detail["sources"],
        }

    async def get_career_skills(self, slug: str) -> list[dict] | None:
        """Return just the skills for a career."""
        career = await self.repo.get_by_slug(slug)
        if career is None:
            return None
        skills = await self.repo.get_skills(career.id)
        return [
            {
                "skill_name": s.skill_name,
                "category": s.category,
                "importance": s.importance,
                "minimum_level": s.minimum_level,
                "description": s.description,
            }
            for s in skills
        ]
