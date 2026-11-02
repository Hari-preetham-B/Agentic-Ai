"""Two-user authorization isolation integration test.

Tests application-layer ownership enforcement against the real database
(PostgreSQL via SQLAlchemy async). This proves that User A cannot access
User B's records through the service layer.

IMPORTANT: This test verifies APPLICATION-LAYER authorization, NOT
PostgreSQL RLS. FastAPI connects to Supabase PostgreSQL as the ``postgres``
owner role, which bypasses RLS. The effective authorization boundary is
the FastAPI application layer (get_current_user dependency + ownership
checks in profile_service.py).

Run with:
    RUN_POSTGRES_INTEGRATION=1 python -m pytest tests/test_auth_isolation.py -v

Skips cleanly when DATABASE_URL is not configured or
RUN_POSTGRES_INTEGRATION is not set.
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.database import set_engine_for_testing
from app.models.profile import Profile
from app.schemas.profile import (
    CareerGoalCreate,
    EducationCreate,
    ExperienceCreate,
    ProfileCreate,
    ProfileUpdate,
    ProjectCreate,
    SkillCreate,
    SkillUpdate,
)
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
)


# ---------------------------------------------------------------------------
# Test user identities
# ---------------------------------------------------------------------------

USER_A_ID = "00000000-0000-0000-0000-00000000000a"
USER_B_ID = "00000000-0000-0000-0000-00000000000b"


# ---------------------------------------------------------------------------
# Helper: create a fresh engine + session for each test
# ---------------------------------------------------------------------------

async def _make_session() -> AsyncSession:
    """Create a fresh engine and session bound to the current event loop."""
    if os.environ.get("RUN_POSTGRES_INTEGRATION") != "1":
        pytest.skip(
            "Set RUN_POSTGRES_INTEGRATION=1 to run PostgreSQL isolation tests"
        )
    settings = get_settings()
    database_url = settings.database_url
    if not database_url:
        pytest.skip("DATABASE_URL not configured")
    engine = create_async_engine(database_url, echo=False, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    session = factory()
    await session.__aenter__()
    # Store engine for cleanup
    session._engine = engine  # type: ignore[attr-defined]
    return session


async def _close_session(session: AsyncSession):
    """Close session and dispose engine."""
    await session.__aexit__(None, None, None)
    engine = getattr(session, "_engine", None)
    if engine is not None:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Helper: cleanup profiles for a user
# ---------------------------------------------------------------------------

async def _cleanup_user_profiles(session: AsyncSession, user_id: str):
    """Delete all profiles owned by a user (cleanup helper)."""
    await session.execute(delete(Profile).where(Profile.user_id == user_id))
    await session.commit()


# ---------------------------------------------------------------------------
# User A tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_a_can_create_profile():
    """User A can create their own profile."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Software Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        assert profile is not None
        assert str(profile.user_id) == USER_A_ID
        assert profile.full_name == "User A"
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_a_can_read_own_profile():
    """User A can read their own profile."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Software Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        fetched = await get_profile(session, profile.id, user_id=USER_A_ID)
        assert fetched is not None
        assert str(fetched.user_id) == USER_A_ID
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_a_can_update_own_profile():
    """User A can update their own profile."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Junior Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        updated = await update_profile(
            session, profile.id, ProfileUpdate(headline="Senior Engineer"),
            user_id=USER_A_ID,
        )
        assert updated is not None
        assert updated.headline == "Senior Engineer"
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_a_can_create_child_records():
    """User A can create education, skills, projects, experience, career goals."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        # Education
        edu = await add_child(
            session, profile.id, "education",
            EducationCreate(
                institution="Test University",
                degree="BS",
                field_of_study="Computer Science",
            ),
            user_id=USER_A_ID,
        )
        assert edu is not None

        # Skill
        skill = await add_child(
            session, profile.id, "skills",
            SkillCreate(name="Python", proficiency="EXPERT", source="USER_CONFIRMED"),
            user_id=USER_A_ID,
        )
        assert skill is not None

        # Project
        project = await add_child(
            session, profile.id, "projects",
            ProjectCreate(name="Test Project", description="A test project"),
            user_id=USER_A_ID,
        )
        assert project is not None

        # Experience
        exp = await add_child(
            session, profile.id, "experience",
            ExperienceCreate(
                organization="Test Corp",
                role="Engineer",
            ),
            user_id=USER_A_ID,
        )
        assert exp is not None

        # Career goal
        goal = await add_child(
            session, profile.id, "career-goals",
            CareerGoalCreate(target_role="Senior Engineer"),
            user_id=USER_A_ID,
        )
        assert goal is not None
    finally:
        await _close_session(session)


# ---------------------------------------------------------------------------
# User B isolation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_b_cannot_read_user_a_profile():
    """User B cannot read User A's profile (application-layer enforcement)."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)
        await _cleanup_user_profiles(session, USER_B_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        # User B tries to read User A's profile
        fetched = await get_profile(session, profile.id, user_id=USER_B_ID)
        assert fetched is None, "User B should NOT be able to read User A's profile"
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_b_cannot_update_user_a_profile():
    """User B cannot update User A's profile."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)
        await _cleanup_user_profiles(session, USER_B_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        updated = await update_profile(
            session, profile.id,
            ProfileUpdate(headline="Hacked by User B"),
            user_id=USER_B_ID,
        )
        assert updated is None, "User B should NOT be able to update User A's profile"
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_profile():
    """User B cannot delete User A's profile."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)
        await _cleanup_user_profiles(session, USER_B_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        deleted = await delete_profile(session, profile.id, user_id=USER_B_ID)
        assert deleted is False, "User B should NOT be able to delete User A's profile"

        # Verify User A's profile still exists
        fetched = await get_profile(session, profile.id, user_id=USER_A_ID)
        assert fetched is not None, "User A's profile should still exist"
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_b_cannot_access_user_a_child_records():
    """User B cannot access User A's child records (indirect ownership via profiles.user_id)."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)
        await _cleanup_user_profiles(session, USER_B_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        # User A creates a skill
        skill = await add_child(
            session, profile.id, "skills",
            SkillCreate(name="Python", proficiency="EXPERT", source="USER_CONFIRMED"),
            user_id=USER_A_ID,
        )
        assert skill is not None

        # User B tries to update User A's skill
        updated = await update_child(
            session, profile.id, "skills", skill.id,
            SkillUpdate(proficiency="BEGINNER"),
            user_id=USER_B_ID,
        )
        assert updated is None, "User B should NOT be able to update User A's skill"

        # User B tries to delete User A's skill
        deleted = await delete_child(
            session, profile.id, "skills", skill.id,
            user_id=USER_B_ID,
        )
        assert deleted is False, "User B should NOT be able to delete User A's skill"

        # User B tries to list User A's skills
        skills = await list_children(
            session, profile.id, "skills", user_id=USER_B_ID
        )
        assert len(skills) == 0, "User B should NOT see User A's skills"
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_a_cross_table_isolation():
    """User A's isolation across all child record types."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)
        await _cleanup_user_profiles(session, USER_B_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        # Create one record of each type
        edu = await add_child(
            session, profile.id, "education",
            EducationCreate(institution="Uni", degree="BS"),
            user_id=USER_A_ID,
        )
        skill = await add_child(
            session, profile.id, "skills",
            SkillCreate(name="Python", proficiency="EXPERT"),
            user_id=USER_A_ID,
        )
        project = await add_child(
            session, profile.id, "projects",
            ProjectCreate(name="Proj", description="Desc"),
            user_id=USER_A_ID,
        )
        exp = await add_child(
            session, profile.id, "experience",
            ExperienceCreate(organization="Org", role="Role"),
            user_id=USER_A_ID,
        )
        goal = await add_child(
            session, profile.id, "career-goals",
            CareerGoalCreate(target_role="Senior"),
            user_id=USER_A_ID,
        )

        # User B tries to access each record type
        assert await get_profile(session, profile.id, user_id=USER_B_ID) is None
        assert await update_child(
            session, profile.id, "education", edu.id,
            EducationCreate(institution="Hacked", degree="BS"),
            user_id=USER_B_ID,
        ) is None
        assert await update_child(
            session, profile.id, "skills", skill.id,
            SkillUpdate(proficiency="BEGINNER"),
            user_id=USER_B_ID,
        ) is None
        assert await update_child(
            session, profile.id, "projects", project.id,
            ProjectCreate(name="Hacked", description="Desc"),
            user_id=USER_B_ID,
        ) is None
        assert await update_child(
            session, profile.id, "experience", exp.id,
            ExperienceCreate(organization="Hacked", role="Role"),
            user_id=USER_B_ID,
        ) is None
        assert await update_child(
            session, profile.id, "career-goals", goal.id,
            CareerGoalCreate(target_role="Hacked"),
            user_id=USER_B_ID,
        ) is None
    finally:
        await _close_session(session)


# ---------------------------------------------------------------------------
# Detail endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_a_can_read_own_profile_detail():
    """User A can read their own profile with all children."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        detail = await get_profile_detail(session, profile.id, user_id=USER_A_ID)
        assert detail is not None
        assert str(detail.user_id) == USER_A_ID
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_b_cannot_read_user_a_profile_detail():
    """User B cannot read User A's profile detail."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)
        await _cleanup_user_profiles(session, USER_B_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        detail = await get_profile_detail(session, profile.id, user_id=USER_B_ID)
        assert detail is None, "User B should NOT be able to read User A's profile detail"
    finally:
        await _close_session(session)


# ---------------------------------------------------------------------------
# Confirmation tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_a_can_confirm_own_profile():
    """User A can confirm their own profile."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
            profile_status="DRAFT",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        # Add required child records for confirmation
        await add_child(
            session, profile.id, "skills",
            SkillCreate(name="Python", proficiency="EXPERT", source="USER_CONFIRMED"),
            user_id=USER_A_ID,
        )
        await add_child(
            session, profile.id, "career-goals",
            CareerGoalCreate(target_role="Senior Engineer"),
            user_id=USER_A_ID,
        )

        confirmed, validation = await confirm_profile(
            session, profile.id, user_id=USER_A_ID
        )
        assert confirmed is not None
        assert confirmed.profile_status == "CONFIRMED"
    finally:
        await _close_session(session)


@pytest.mark.asyncio
async def test_user_b_cannot_confirm_user_a_profile():
    """User B cannot confirm User A's profile."""
    session = await _make_session()
    try:
        await _cleanup_user_profiles(session, USER_A_ID)
        await _cleanup_user_profiles(session, USER_B_ID)

        data = ProfileCreate(
            full_name="User A",
            headline="Engineer",
            email="usera@example.com",
            profile_status="DRAFT",
        )
        profile = await create_profile(session, data, user_id=USER_A_ID)

        confirmed, validation = await confirm_profile(
            session, profile.id, user_id=USER_B_ID
        )
        assert confirmed is None, "User B should NOT be able to confirm User A's profile"
    finally:
        await _close_session(session)
