"""Profile application service.

Coordinates persistence, validation, and confirmation of CareerTwin profiles
and their child records. SQLAlchemy models are mapped to/from Pydantic
schemas here; routes never touch the ORM directly.
"""

from typing import List, Optional, Sequence, Type, TypeVar

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


async def _get_profile_or_404(
    session: AsyncSession, profile_id
) -> Optional[Profile]:
    result = await session.execute(select(Profile).where(Profile.id == profile_id))
    return result.scalar_one_or_none()


async def create_profile(session: AsyncSession, data: ProfileCreate) -> Profile:
    profile = Profile(
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


async def get_profile(session: AsyncSession, profile_id) -> Optional[Profile]:
    return await _get_profile_or_404(session, profile_id)


async def get_profile_detail(session: AsyncSession, profile_id) -> Optional[Profile]:
    """Load a profile with all children eagerly attached."""
    from sqlalchemy.orm import selectinload

    result = await session.execute(
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


async def update_profile(
    session: AsyncSession, profile_id, data: ProfileUpdate
) -> Optional[Profile]:
    profile = await _get_profile_or_404(session, profile_id)
    if profile is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)
    await session.flush()
    await session.refresh(profile)
    return profile


async def delete_profile(session: AsyncSession, profile_id) -> bool:
    profile = await _get_profile_or_404(session, profile_id)
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


async def add_child(
    session: AsyncSession,
    profile_id,
    section: str,
    data,
):
    """Add a child record to a profile."""
    profile = await _get_profile_or_404(session, profile_id)
    if profile is None:
        return None
    model_cls, _create_schema, _response_schema = _MODEL_MAP[section]
    instance = model_cls(profile_id=profile_id, **data.model_dump())
    session.add(instance)
    await session.flush()
    await session.refresh(instance)
    return instance


async def list_children(
    session: AsyncSession, profile_id, section: str
) -> Sequence:
    """List child records for a profile."""
    model_cls, _create_schema, _response_schema = _MODEL_MAP[section]
    result = await session.execute(
        select(model_cls).where(model_cls.profile_id == profile_id)
    )
    return result.scalars().all()


async def update_child(
    session: AsyncSession, profile_id, section: str, child_id, data
):
    """Update a child record belonging to a profile."""
    model_cls, _create_schema, _response_schema = _MODEL_MAP[section]
    result = await session.execute(
        select(model_cls).where(
            model_cls.id == child_id, model_cls.profile_id == profile_id
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(instance, field, value)
    await session.flush()
    await session.refresh(instance)
    return instance


async def delete_child(session: AsyncSession, profile_id, section: str, child_id) -> bool:
    """Delete a child record belonging to a profile."""
    model_cls, _create_schema, _response_schema = _MODEL_MAP[section]
    result = await session.execute(
        select(model_cls).where(
            model_cls.id == child_id, model_cls.profile_id == profile_id
        )
    )
    instance = result.scalar_one_or_none()
    if instance is None:
        return False
    await session.delete(instance)
    await session.flush()
    return True


# ---------------------------------------------------------------------------
# Validation & confirmation
# ---------------------------------------------------------------------------


async def validate_profile_for_confirmation(
    session: AsyncSession, profile_id
):
    """Validate a profile and its children; return a ValidationResult."""
    profile = await get_profile_detail(session, profile_id)
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
            SkillCreate.model_validate(s, from_attributes=True) for s in profile.skills
        ],
        projects=[
            ProjectCreate.model_validate(p, from_attributes=True) for p in profile.projects
        ],
        experience=[
            ExperienceCreate.model_validate(e, from_attributes=True)
            for e in profile.experience
        ],
        career_goals=list(profile.career_goals),
    )


async def confirm_profile(session: AsyncSession, profile_id):
    """Confirm a profile after validation.

    Returns (profile, validation_result). If validation fails, profile is
    returned unchanged with status not set to CONFIRMED.
    """
    profile = await get_profile_detail(session, profile_id)
    if profile is None:
        return None, None

    validation = await validate_profile_for_confirmation(session, profile_id)
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
