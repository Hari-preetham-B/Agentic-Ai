"""Profile application service.

Coordinates persistence, validation, and confirmation of CareerTwin profiles
and their child records. SQLAlchemy models are mapped to/from Pydantic
schemas here; routes never touch the ORM directly.

When a ``user_id`` is provided, all operations enforce application-layer
ownership: a user can only access profiles and child records where
``profiles.user_id`` matches the authenticated user's ID. This is the
effective authorization boundary because FastAPI connects to PostgreSQL as
the ``postgres`` owner role, which bypasses PostgreSQL RLS (see
docs/EXTERNAL_PROVIDERS.md for details).

When ``user_id`` is ``None`` (used by existing tests that call services
directly), no ownership filter is applied for backward compatibility.
"""

from typing import List, Optional, Sequence, Type, TypeVar
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.profile import (
    CareerGoal,
    Education,
    Experience,
    Profile,
    Project,
    Skill,
)
from app.schemas.profile import (
    CareerGoalCreate,
    CareerGoalResponse,
    CareerGoalUpdate,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    ExperienceCreate,
    ExperienceResponse,
    ExperienceUpdate,
    ProfileCreate,
    ProfileDetailResponse,
    ProfileResponse,
    ProfileUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
)
from app.services.validation import validate_for_confirmation

M = TypeVar("M")


def _ownership_filter(user_id: Optional[str]):
    """Return a SQLAlchemy where clause filtering profiles by user_id.

    When user_id is None, returns a clause that is always true (no filter).
    """
    if user_id is None:
        return Profile.id.is_not(None)  # always true
    return Profile.user_id == user_id


async def _get_profile_or_404(
    session: AsyncSession, profile_id, user_id: Optional[str] = None
) -> Optional[Profile]:
    result = await session.execute(
        select(Profile).where(
            Profile.id == profile_id,
            _ownership_filter(user_id),
        )
    )
    return result.scalar_one_or_none()


async def create_profile(
    session: AsyncSession, data: ProfileCreate, user_id: Optional[str] = None
) -> Profile:
    profile = Profile(
        id=uuid.uuid4(),
        user_id=user_id,
        full_name=data.full_name,
        headline=data.headline,
        email=data.email,
        phone=data.phone,
        location=data.location,
        summary=data.summary,
        profile_status=data.profile_status or "DRAFT",
    )
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    return profile


async def get_profile(
    session: AsyncSession, profile_id, user_id: Optional[str] = None
) -> Optional[Profile]:
    return await _get_profile_or_404(session, profile_id, user_id)


async def get_profile_detail(
    session: AsyncSession, profile_id, user_id: Optional[str] = None
) -> Optional[Profile]:
    """Load a profile with all children eagerly attached.

    Enforces ownership when user_id is provided.
    """
    from sqlalchemy.orm import selectinload

    result = await session.execute(
        select(Profile)
        .where(Profile.id == profile_id, _ownership_filter(user_id))
        .options(
            selectinload(Profile.education),
            selectinload(Profile.skills),
            selectinload(Profile.projects),
            selectinload(Profile.experience),
            selectinload(Profile.career_goals),
        )
    )
    return result.scalar_one_or_none()


async def update_profile(
    session: AsyncSession, profile_id, data: ProfileUpdate, user_id: Optional[str] = None
) -> Optional[Profile]:
    profile = await _get_profile_or_404(session, profile_id, user_id)
    if profile is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    await session.flush()
    await session.refresh(profile)
    return profile


async def delete_profile(
    session: AsyncSession, profile_id, user_id: Optional[str] = None
) -> bool:
    profile = await _get_profile_or_404(session, profile_id, user_id)
    if profile is None:
        return False
    await session.delete(profile)
    await session.flush()
    return True


# ---------------------------------------------------------------------------
# Child records
# ---------------------------------------------------------------------------

_MODEL_MAP = {
    "education": (Education, EducationCreate, EducationResponse),
    "skills": (Skill, SkillCreate, SkillResponse),
    "projects": (Project, ProjectCreate, ProjectResponse),
    "experience": (Experience, ExperienceCreate, ExperienceResponse),
    "career-goals": (CareerGoal, CareerGoalCreate, CareerGoalResponse),
}


async def _get_child_or_404(
    session: AsyncSession,
    model_cls: Type[M],
    profile_id,
    child_id,
    user_id: Optional[str] = None,
) -> Optional[M]:
    """Fetch a child record, enforcing profile ownership via join."""
    where_conditions = [
        model_cls.id == child_id,
        model_cls.profile_id == profile_id,
    ]
    if user_id is not None:
        where_conditions.append(Profile.user_id == user_id)

    result = await session.execute(
        select(model_cls)
        .join(Profile, model_cls.profile_id == Profile.id)
        .where(*where_conditions)
    )
    return result.scalar_one_or_none()


async def add_child(
    session: AsyncSession,
    profile_id,
    section: str,
    data,
    user_id: Optional[str] = None,
):
    """Add a child record to a profile.

    Enforces ownership when user_id is provided.
    """
    profile = await _get_profile_or_404(session, profile_id, user_id)
    if profile is None:
        return None
    model_cls, _create_schema, _response_schema = _MODEL_MAP[section]
    instance = model_cls(profile_id=profile_id, **data.model_dump())
    session.add(instance)
    await session.flush()
    await session.refresh(instance)
    return instance


async def list_children(
    session: AsyncSession, profile_id, section: str, user_id: Optional[str] = None
) -> Sequence:
    """List child records for a profile.

    Enforces ownership when user_id is provided.
    """
    model_cls, _create_schema, _response_schema = _MODEL_MAP[section]
    # First verify profile ownership (if user_id provided)
    if user_id is not None:
        profile = await _get_profile_or_404(session, profile_id, user_id)
        if profile is None:
            return []
    result = await session.execute(
        select(model_cls).where(model_cls.profile_id == profile_id)
    )
    return result.scalars().all()


async def update_child(
    session: AsyncSession,
    profile_id,
    section: str,
    child_id,
    data,
    user_id: Optional[str] = None,
):
    """Update a child record belonging to a profile.

    Enforces ownership when user_id is provided.
    """
    model_cls, _create_schema, _response_schema = _MODEL_MAP[section]
    instance = await _get_child_or_404(
        session, model_cls, profile_id, child_id, user_id
    )
    if instance is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(instance, field, value)
    await session.flush()
    await session.refresh(instance)
    return instance


async def delete_child(
    session: AsyncSession,
    profile_id,
    section: str,
    child_id,
    user_id: Optional[str] = None,
) -> bool:
    """Delete a child record belonging to a profile.

    Enforces ownership when user_id is provided.
    """
    model_cls, _create_schema, _response_schema = _MODEL_MAP[section]
    instance = await _get_child_or_404(
        session, model_cls, profile_id, child_id, user_id
    )
    if instance is None:
        return False
    await session.delete(instance)
    await session.flush()
    return True


# ---------------------------------------------------------------------------
# Validation & confirmation
# ---------------------------------------------------------------------------


async def validate_profile_for_confirmation(
    session: AsyncSession, profile_id, user_id: Optional[str] = None
):
    """Validate a profile and its children; return a ValidationResult.

    Enforces profile ownership when user_id is provided.
    """
    profile = await get_profile_detail(session, profile_id, user_id)
    if profile is None:
        from app.schemas.profile import ValidationErrorDetail, ValidationResult

        return ValidationResult(
            valid=False,
            errors=[
                ValidationErrorDetail(
                    field="profile",
                    code="NOT_FOUND",
                    message="Profile not found.",
                )
            ],
            warnings=[],
        )

    from app.schemas.profile import (
        EducationCreate,
        ExperienceCreate,
        ProjectCreate,
        SkillCreate,
        ValidationResult,
    )

    return validate_for_confirmation(
        profile=ProfileCreate.model_validate(profile, from_attributes=True),
        education=[
            EducationCreate.model_validate(e, from_attributes=True)
            for e in profile.education
        ],
        skills=[
            SkillCreate.model_validate(s, from_attributes=True)
            for s in profile.skills
        ],
        projects=[
            ProjectCreate.model_validate(p, from_attributes=True)
            for p in profile.projects
        ],
        experience=[
            ExperienceCreate.model_validate(e, from_attributes=True)
            for e in profile.experience
        ],
        career_goals=list(profile.career_goals),
    )


async def confirm_profile(
    session: AsyncSession, profile_id, user_id: Optional[str] = None
):
    """Confirm a profile after validation.

    Enforces profile ownership when user_id is provided.
    Returns (profile, validation_result).
    """
    profile = await get_profile_detail(session, profile_id, user_id)
    if profile is None:
        return None, None

    validation = await validate_profile_for_confirmation(
        session, profile_id, user_id
    )
    if not validation.valid:
        return profile, validation

    profile.profile_status = "CONFIRMED"
    await session.flush()
    await session.refresh(profile)
    return profile, validation


# ---------------------------------------------------------------------------
# Response mappers
# ---------------------------------------------------------------------------


def profile_to_detail_response(profile: Profile) -> ProfileDetailResponse:
    return ProfileDetailResponse.model_validate(profile, from_attributes=True)
