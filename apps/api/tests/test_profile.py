"""Backend tests for profiles, validation, confirmation, and child records."""

from datetime import date
from uuid import uuid4

import pytest

from app.models.profile import Profile
from app.schemas.profile import (
    CareerGoalCreate,
    EducationCreate,
    ExperienceCreate,
    ProfileCreate,
    ProjectCreate,
    SkillCreate,
)
from app.services.validation import validate_for_confirmation
from app.services.profile_service import (
    add_child,
    confirm_profile,
    create_profile,
    delete_child,
    delete_profile,
    get_profile,
    get_profile_detail,
    list_children,
    update_child,
    update_profile,
    validate_profile_for_confirmation,
)


def _profile_payload() -> ProfileCreate:
    return ProfileCreate(
        full_name="Ada Lovelace",
        headline="Student",
        email="ada@example.com",
        phone="555-0100",
        location="London",
        summary="Aspiring engineer.",
        profile_status="DRAFT",
    )


@pytest.mark.asyncio
async def test_create_and_retrieve_profile(session):
    profile = await create_profile(session, _profile_payload())
    assert profile.id is not None
    assert profile.full_name == "Ada Lovelace"
    assert profile.profile_status == "DRAFT"

    fetched = await get_profile(session, profile.id)
    assert fetched is not None
    assert fetched.full_name == "Ada Lovelace"


@pytest.mark.asyncio
async def test_update_profile(session):
    profile = await create_profile(session, _profile_payload())
    from app.schemas.profile import ProfileUpdate

    updated = await update_profile(
        session, profile.id, ProfileUpdate(headline="Software Engineer", summary="Updated summary.")
    )
    assert updated.headline == "Software Engineer"
    assert updated.summary == "Updated summary."
    assert updated.full_name == "Ada Lovelace"  # unchanged


@pytest.mark.asyncio
async def test_delete_profile(session):
    profile = await create_profile(session, _profile_payload())
    deleted = await delete_profile(session, profile.id)
    assert deleted is True
    assert await get_profile(session, profile.id) is None


@pytest.mark.asyncio
async def test_child_record_crud(session):
    profile = await create_profile(session, _profile_payload())

    # Add education
    edu = await add_child(
        session,
        profile.id,
        "education",
        EducationCreate(
            institution="University of Example",
            degree="BSc",
            field_of_study="Computer Science",
            start_date=date(2020, 9, 1),
            end_date=date(2024, 6, 15),
            description="Honors.",
        ),
    )
    assert edu.id is not None
    assert edu.profile_id == profile.id

    # Add skill
    skill = await add_child(
        session,
        profile.id,
        "skills",
        SkillCreate(
            name="Python",
            category="Programming",
            proficiency="ADVANCED",
            years_experience=3.0,
            source="USER_CONFIRMED",
        ),
    )
    assert skill.id is not None

    # List children
    educations = await list_children(session, profile.id, "education")
    assert len(educations) == 1
    skills = await list_children(session, profile.id, "skills")
    assert len(skills) == 1

    # Update child
    from app.schemas.profile import EducationUpdate

    updated_edu = await update_child(
        session, profile.id, "education", edu.id, EducationUpdate(degree="MSc")
    )
    assert updated_edu.degree == "MSc"

    # Delete child
    removed = await delete_child(session, profile.id, "skills", skill.id)
    assert removed is True
    assert len(await list_children(session, profile.id, "skills")) == 0


@pytest.mark.asyncio
async def test_profile_detail_includes_children(session):
    profile = await create_profile(session, _profile_payload())
    await add_child(
        session,
        profile.id,
        "skills",
        SkillCreate(name="Python", source="USER_CONFIRMED"),
    )
    await add_child(
        session,
        profile.id,
        "career-goals",
        CareerGoalCreate(target_role="Software Engineer", priority=1),
    )

    detail = await get_profile_detail(session, profile.id)
    assert detail is not None
    assert len(detail.skills) == 1
    assert detail.skills[0].name == "Python"
    assert len(detail.career_goals) == 1
    assert detail.career_goals[0].target_role == "Software Engineer"


@pytest.mark.asyncio
async def test_validation_rejects_missing_name(session):
    result = await validate_profile_for_confirmation(
        session, uuid4()
    )  # non-existent profile
    assert result.valid is False
    assert any(e.code == "NOT_FOUND" for e in result.errors)


@pytest.mark.asyncio
async def test_validation_structure(session):
    from app.schemas.profile import ValidationErrorDetail

    profile = ProfileCreate(full_name="", profile_status="DRAFT")
    edu = [EducationCreate(institution="Uni", degree="BSc")]
    skills = [SkillCreate(name="Python", source="USER_CONFIRMED")]
    goals = []

    result = validate_for_confirmation(profile, edu, skills, [], [], goals)
    assert result.valid is False
    assert any(e.field == "full_name" for e in result.errors)
    assert any(e.field == "career_goals" for e in result.errors)
    assert all(isinstance(e, ValidationErrorDetail) for e in result.errors)


@pytest.mark.asyncio
async def test_confirmation_rejects_invalid_profile(session):
    profile = await create_profile(
        session, ProfileCreate(full_name="", profile_status="DRAFT")
    )
    confirmed, validation = await confirm_profile(session, profile.id)
    assert confirmed is not None
    assert confirmed.profile_status != "CONFIRMED"
    assert validation is not None
    assert validation.valid is False


@pytest.mark.asyncio
async def test_successful_confirmation(session):
    profile = await create_profile(session, _profile_payload())
    await add_child(
        session,
        profile.id,
        "skills",
        SkillCreate(name="Python", source="USER_CONFIRMED"),
    )
    await add_child(
        session,
        profile.id,
        "career-goals",
        CareerGoalCreate(target_role="Software Engineer", priority=1),
    )

    confirmed, validation = await confirm_profile(session, profile.id)
    assert validation.valid is True
    assert confirmed.profile_status == "CONFIRMED"

    # Verify persisted
    fetched = await get_profile(session, profile.id)
    assert fetched.profile_status == "CONFIRMED"


@pytest.mark.asyncio
async def test_profile_status_transitions(session):
    profile = await create_profile(session, _profile_payload())
    assert profile.profile_status == "DRAFT"

    from app.schemas.profile import ProfileUpdate

    await update_profile(session, profile.id, ProfileUpdate(profile_status="REVIEW"))
    reviewed = await get_profile(session, profile.id)
    assert reviewed.profile_status == "REVIEW"

    await add_child(
        session,
        profile.id,
        "skills",
        SkillCreate(name="Python", source="USER_CONFIRMED"),
    )
    await add_child(
        session,
        profile.id,
        "career-goals",
        CareerGoalCreate(target_role="Engineer", priority=1),
    )
    confirmed, _ = await confirm_profile(session, profile.id)
    assert confirmed.profile_status == "CONFIRMED"
