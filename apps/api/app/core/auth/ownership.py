"""Application-layer ownership enforcement.

FastAPI connects to PostgreSQL with the database owner role, which bypasses
PostgreSQL RLS. Every user-owned resource therefore must be filtered by the
authenticated user's ID in the application layer.

These helpers load a profile only when it belongs to the authenticated user,
and raise 404 (not 403) otherwise so the API does not disclose whether a
resource exists for another user.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile


def parse_uuid(value: str | UUID) -> UUID | None:
    """Return a UUID for ``value`` or None when it is malformed."""
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def normalize_user_id(user_id: str | UUID) -> UUID | None:
    """Normalize an authenticated user ID to the UUID stored in the database.

    Supabase Auth subjects are UUIDs. A malformed subject cannot own any
    profile, so callers treat ``None`` as "not found" rather than querying
    with an incompatible type.
    """
    return parse_uuid(user_id)


async def get_owned_profile(
    session: AsyncSession,
    profile_id: str | UUID,
    user_id: str | UUID,
) -> Profile | None:
    """Return the profile when it belongs to ``user_id``, else None."""
    pid = parse_uuid(profile_id)
    uid = normalize_user_id(user_id)
    if pid is None or uid is None:
        return None
    result = await session.execute(
        select(Profile).where(Profile.id == pid, Profile.user_id == uid)
    )
    return result.scalar_one_or_none()


async def require_owned_profile(
    session: AsyncSession,
    profile_id: str | UUID,
    user_id: str,
) -> Profile:
    """Return the owned profile or raise 404."""
    profile = await get_owned_profile(session, profile_id, user_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found"
        )
    return profile


async def require_owned_interview_session(session, session_id: str, user_id: str):
    """Load an interview session only when its profile belongs to the user."""
    from app.models.interview import InterviewSession

    sid = parse_uuid(session_id)
    uid = normalize_user_id(user_id)
    if sid is None or uid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    result = await session.execute(
        select(InterviewSession)
        .join(Profile, InterviewSession.profile_id == Profile.id)
        .where(InterviewSession.id == sid, Profile.user_id == uid)
    )
    interview_session = result.scalar_one_or_none()
    if interview_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    return interview_session


async def require_owned_roadmap(session, roadmap_id: str, user_id: str):
    """Load a roadmap only when its profile belongs to the user."""
    from app.models.learning import Roadmap

    rid = parse_uuid(roadmap_id)
    uid = normalize_user_id(user_id)
    if rid is None or uid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found"
        )
    result = await session.execute(
        select(Roadmap)
        .join(Profile, Roadmap.profile_id == Profile.id)
        .where(Roadmap.id == rid, Profile.user_id == uid)
    )
    roadmap = result.scalar_one_or_none()
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Roadmap not found"
        )
    return roadmap


async def require_owned_claim(session, claim_id: str, user_id: str):
    """Load a claim only when its profile belongs to the user."""
    from app.models.evidence import Claim

    cid = parse_uuid(claim_id)
    uid = normalize_user_id(user_id)
    if cid is None or uid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found"
        )
    result = await session.execute(
        select(Claim)
        .join(Profile, Claim.profile_id == Profile.id)
        .where(Claim.id == cid, Profile.user_id == uid)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found"
        )
    return claim


async def require_owned_agent_run(session, run_id, user_id: str):
    """Load an agent run only when its profile belongs to the user."""
    from app.models.profile import AgentRun

    rid = parse_uuid(run_id)
    uid = normalize_user_id(user_id)
    if rid is None or uid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found"
        )
    result = await session.execute(
        select(AgentRun)
        .join(Profile, AgentRun.profile_id == Profile.id)
        .where(AgentRun.id == rid, Profile.user_id == uid)
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found"
        )
    return run


__all__ = [
    "parse_uuid",
    "normalize_user_id",
    "get_owned_profile",
    "require_owned_profile",
    "require_owned_interview_session",
    "require_owned_roadmap",
    "require_owned_claim",
    "require_owned_agent_run",
]
