"""Repository layer.

Database access belongs to repositories/services. Agents never execute SQL or
manipulate SQLAlchemy sessions directly.
"""

from __future__ import annotations

from typing import Any, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.career import (
    Career,
    CareerProject,
    CareerSkill,
    CareerSource,
    CareerTool,
)
from app.models.profile import AgentEvent, AgentRun, Profile


class ProfileRepository:
    """Repository for profile read/write access."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, profile_id: UUID) -> Profile | None:
        result = await self.session.execute(
            select(Profile)
            .where(Profile.id == profile_id)
            .options(
                selectinload(Profile.education),
                selectinload(Profile.skills),
                selectinload(Profile.projects),
                selectinload(Profile.experience),
                selectinload(Profile.career_goals),
            )
        )
        return result.scalar_one_or_none()


class AgentRunRepository:
    """Repository for agent run persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, run: AgentRun) -> AgentRun:
        self.session.add(run)
        await self.session.commit()
        await self.session.refresh(run)
        return run

    async def get(self, run_id: UUID) -> AgentRun | None:
        result = await self.session.execute(
            select(AgentRun).where(AgentRun.id == run_id)
        )
        return result.scalar_one_or_none()

    async def list_by_profile(
        self, profile_id: UUID, limit: int = 50
    ) -> Sequence[AgentRun]:
        result = await self.session.execute(
            select(AgentRun)
            .where(AgentRun.profile_id == profile_id)
            .order_by(AgentRun.started_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def update_status(
        self,
        run: AgentRun,
        *,
        status: str | None = None,
        error: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        completed: bool = False,
    ) -> AgentRun:
        if status is not None:
            run.status = status
        if error is not None:
            run.error = error
        if provider is not None:
            run.provider = provider
        if model is not None:
            run.model = model
        if completed:
            from sqlalchemy import func

            run.completed_at = func.now()  # type: ignore[assignment]
        await self.session.commit()
        await self.session.refresh(run)
        return run


class AgentEventRepository:
    """Repository for agent event persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, event: AgentEvent) -> AgentEvent:
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def list_for_run(
        self, run_id: UUID
    ) -> Sequence[AgentEvent]:
        result = await self.session.execute(
            select(AgentEvent)
            .where(AgentEvent.agent_run_id == run_id)
            .order_by(AgentEvent.sequence.asc())
        )
        return result.scalars().all()


class CareerRepository:
    """Repository for curated career knowledge."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_careers(self) -> Sequence[Career]:
        result = await self.session.execute(select(Career).order_by(Career.title))
        return result.scalars().all()

    async def get_by_slug(self, slug: str) -> Career | None:
        result = await self.session.execute(
            select(Career).where(Career.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, career_id: UUID) -> Career | None:
        result = await self.session.execute(
            select(Career).where(Career.id == career_id)
        )
        return result.scalar_one_or_none()

    async def get_skills(self, career_id: UUID) -> Sequence[CareerSkill]:
        result = await self.session.execute(
            select(CareerSkill).where(CareerSkill.career_id == career_id)
        )
        return result.scalars().all()

    async def get_tools(self, career_id: UUID) -> Sequence[CareerTool]:
        result = await self.session.execute(
            select(CareerTool).where(CareerTool.career_id == career_id)
        )
        return result.scalars().all()

    async def get_projects(self, career_id: UUID) -> Sequence[CareerProject]:
        result = await self.session.execute(
            select(CareerProject).where(CareerProject.career_id == career_id)
        )
        return result.scalars().all()

    async def get_sources(self, career_id: UUID) -> Sequence[CareerSource]:
        result = await self.session.execute(
            select(CareerSource).where(CareerSource.career_id == career_id)
        )
        return result.scalars().all()


__all__ = [
    "ProfileRepository",
    "AgentRunRepository",
    "AgentEventRepository",
    "CareerRepository",
]
