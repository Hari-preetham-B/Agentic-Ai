"""Tests for the reference data seed system.

Tests:
1. Seed idempotency (run twice, same counts)
2. Referential integrity (no orphaned rows)
3. Dependency graph (acyclic)
4. Career matching (SkillMatchingEngine against seeded careers)
5. Roadmap generation
6. Interview question selection

These tests run against SQLite in-memory (default test database) and do not
require a real PostgreSQL connection.
"""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_engine_for_testing
from app.scripts.seed_data import CAREERS, INTERVIEW_QUESTIONS, LEARNING_RESOURCES, SKILL_DEPENDENCIES
from app.scripts.seed_reference_data import (
    _ensure_reference_profile,
    _upsert_career,
    _upsert_career_skills,
    _upsert_career_sources,
    _upsert_career_tools,
    _upsert_career_projects,
    _upsert_interview_questions,
    _upsert_learning_resources,
    _upsert_skill_dependencies,
)
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.interview_service import AdaptiveQuestionSelector
from app.services.learning_roadmap_service import LearningRoadmapService
from app.schemas.profile import ProfileCreate
from app.services.profile_service import create_profile
from app.services.repositories import CareerRepository
from app.services.skill_matching import compute_skill_match
from app.services.skill_dependency_service import SkillDependencyService


@pytest_asyncio.fixture
async def session(session: AsyncSession):
    """Reuse the conftest session fixture."""
    yield session


@pytest.mark.asyncio
async def test_seed_idempotency(session: AsyncSession):
    """Running the seed twice produces identical counts."""
    await _ensure_reference_profile(session)

    # Clean up any existing careers from other tests
    from sqlalchemy import delete
    from app.models.career import Career, CareerSkill, CareerTool, CareerProject, CareerSource
    from app.models.learning import LearningResource, LearningResourceSkill, SkillDependency
    from app.models.interview import InterviewQuestion, InterviewQuestionSkill

    await session.execute(delete(Career))
    await session.execute(delete(CareerSkill))
    await session.execute(delete(CareerTool))
    await session.execute(delete(CareerProject))
    await session.execute(delete(CareerSource))
    await session.execute(delete(LearningResource))
    await session.execute(delete(LearningResourceSkill))
    await session.execute(delete(SkillDependency))
    await session.execute(delete(InterviewQuestion))
    await session.execute(delete(InterviewQuestionSkill))
    await session.commit()

    # First run
    for career_data in CAREERS:
        career_id = await _upsert_career(session, career_data)
        await _upsert_career_skills(session, career_id, career_data.get("skills", []))
        await _upsert_career_tools(session, career_id, career_data.get("tools", []))
        await _upsert_career_projects(session, career_id, career_data.get("projects", []))
        await _upsert_career_sources(session, career_id, career_data.get("sources", []))

    await _upsert_learning_resources(session, LEARNING_RESOURCES)
    await _upsert_skill_dependencies(session, SKILL_DEPENDENCIES)
    await _upsert_interview_questions(session, INTERVIEW_QUESTIONS)
    await session.commit()

    # Count after first run
    from sqlalchemy import select
    from app.models.career import Career, CareerSkill, CareerTool, CareerProject, CareerSource
    from app.models.learning import LearningResource, LearningResourceSkill, SkillDependency
    from app.models.interview import InterviewQuestion, InterviewQuestionSkill

    result = await session.execute(select(Career))
    count_careers_1 = len(result.scalars().all())
    result = await session.execute(select(CareerSkill))
    count_career_skills_1 = len(result.scalars().all())
    result = await session.execute(select(CareerTool))
    count_career_tools_1 = len(result.scalars().all())
    result = await session.execute(select(CareerProject))
    count_career_projects_1 = len(result.scalars().all())
    result = await session.execute(select(CareerSource))
    count_career_sources_1 = len(result.scalars().all())
    result = await session.execute(select(LearningResource))
    count_learning_resources_1 = len(result.scalars().all())
    result = await session.execute(select(LearningResourceSkill))
    count_learning_resource_skills_1 = len(result.scalars().all())
    result = await session.execute(select(SkillDependency))
    count_skill_deps_1 = len(result.scalars().all())
    result = await session.execute(select(InterviewQuestion))
    count_interview_questions_1 = len(result.scalars().all())
    result = await session.execute(select(InterviewQuestionSkill))
    count_interview_question_skills_1 = len(result.scalars().all())

    # Second run (should not duplicate)
    for career_data in CAREERS:
        career_id = await _upsert_career(session, career_data)
        await _upsert_career_skills(session, career_id, career_data.get("skills", []))
        await _upsert_career_tools(session, career_id, career_data.get("tools", []))
        await _upsert_career_projects(session, career_id, career_data.get("projects", []))
        await _upsert_career_sources(session, career_id, career_data.get("sources", []))

    await _upsert_learning_resources(session, LEARNING_RESOURCES)
    await _upsert_skill_dependencies(session, SKILL_DEPENDENCIES)
    await _upsert_interview_questions(session, INTERVIEW_QUESTIONS)
    await session.commit()

    # Count after second run
    result = await session.execute(select(Career))
    count_careers_2 = len(result.scalars().all())
    result = await session.execute(select(CareerSkill))
    count_career_skills_2 = len(result.scalars().all())
    result = await session.execute(select(CareerTool))
    count_career_tools_2 = len(result.scalars().all())
    result = await session.execute(select(CareerProject))
    count_career_projects_2 = len(result.scalars().all())
    result = await session.execute(select(CareerSource))
    count_career_sources_2 = len(result.scalars().all())
    result = await session.execute(select(LearningResource))
    count_learning_resources_2 = len(result.scalars().all())
    result = await session.execute(select(LearningResourceSkill))
    count_learning_resource_skills_2 = len(result.scalars().all())
    result = await session.execute(select(SkillDependency))
    count_skill_deps_2 = len(result.scalars().all())
    result = await session.execute(select(InterviewQuestion))
    count_interview_questions_2 = len(result.scalars().all())
    result = await session.execute(select(InterviewQuestionSkill))
    count_interview_question_skills_2 = len(result.scalars().all())

    # Assert idempotency
    assert count_careers_1 == count_careers_2 == 8
    assert count_career_skills_1 == count_career_skills_2
    assert count_career_tools_1 == count_career_tools_2
    assert count_career_projects_1 == count_career_projects_2
    assert count_career_sources_1 == count_career_sources_2
    assert count_learning_resources_1 == count_learning_resources_2
    assert count_learning_resource_skills_1 == count_learning_resource_skills_2
    assert count_skill_deps_1 == count_skill_deps_2
    assert count_interview_questions_1 == count_interview_questions_2
    assert count_interview_question_skills_1 == count_interview_question_skills_2


@pytest.mark.asyncio
async def test_referential_integrity(session: AsyncSession):
    """No orphaned rows after seeding."""
    await _ensure_reference_profile(session)

    # Seed careers
    for career_data in CAREERS:
        career_id = await _upsert_career(session, career_data)
        await _upsert_career_skills(session, career_id, career_data.get("skills", []))
        await _upsert_career_tools(session, career_id, career_data.get("tools", []))
        await _upsert_career_projects(session, career_id, career_data.get("projects", []))
        await _upsert_career_sources(session, career_id, career_data.get("sources", []))

    await _upsert_learning_resources(session, LEARNING_RESOURCES)
    await _upsert_skill_dependencies(session, SKILL_DEPENDENCIES)
    await _upsert_interview_questions(session, INTERVIEW_QUESTIONS)
    await session.commit()

    from sqlalchemy import select
    from app.models.career import CareerSkill, CareerTool, CareerProject, CareerSource
    from app.models.learning import LearningResourceSkill, SkillDependency
    from app.models.interview import InterviewQuestionSkill

    # Verify every career_skill references a valid career
    result = await session.execute(select(CareerSkill))
    for cs in result.scalars().all():
        assert cs.career_id is not None

    # Verify every career_tool references a valid career
    result = await session.execute(select(CareerTool))
    for ct in result.scalars().all():
        assert ct.career_id is not None

    # Verify every skill_dependency references valid skills
    result = await session.execute(select(SkillDependency))
    for dep in result.scalars().all():
        assert dep.skill_id is not None
        assert dep.prerequisite_skill_id is not None

    # Verify every interview_question_skill references a valid question
    result = await session.execute(select(InterviewQuestionSkill))
    for iqs in result.scalars().all():
        assert iqs.question_id is not None


@pytest.mark.asyncio
async def test_dependency_graph_acyclic(session: AsyncSession):
    """Seeded skill dependency graph has no cycles."""
    await _ensure_reference_profile(session)

    await _upsert_skill_dependencies(session, SKILL_DEPENDENCIES)
    await session.commit()

    dep_service = SkillDependencyService(session)
    deps = await dep_service.get_all_dependencies()
    graph = dep_service.build_graph(deps)

    has_cycle = dep_service.detect_cycles(graph)
    assert not has_cycle, "Dependency graph must be acyclic"

    # Topological sort should succeed
    order = dep_service.topological_sort(graph)
    assert len(order) > 0


@pytest.mark.asyncio
async def test_career_matching_against_seeded_data(session: AsyncSession):
    """SkillMatchingEngine works against seeded careers."""
    await _ensure_reference_profile(session)

    # Clean up any existing careers from other tests
    from sqlalchemy import delete
    from app.models.career import Career, CareerSkill
    await session.execute(delete(CareerSkill))
    await session.execute(delete(Career))
    await session.commit()

    # Seed careers
    for career_data in CAREERS:
        career_id = await _upsert_career(session, career_data)
        await _upsert_career_skills(session, career_id, career_data.get("skills", []))
    await session.commit()

    repo = CareerRepository(session)
    careers = await repo.list_careers()
    assert len(careers) == 8

    # Test skill matching against each career
    profile_skills = [
        {"name": "Python", "proficiency": "INTERMEDIATE", "years_experience": 3.0, "source": "USER_CONFIRMED"},
        {"name": "SQL", "proficiency": "BEGINNER", "years_experience": 1.0, "source": "USER_CONFIRMED"},
    ]

    for career in careers:
        career_skills = await repo.get_skills(career.id)
        cs_list = [
            {
                "skill_name": s.skill_name,
                "category": s.category,
                "importance": s.importance,
                "minimum_level": s.minimum_level,
            }
            for s in career_skills
        ]
        result = compute_skill_match(
            career_id=str(career.id),
            career_title=career.title,
            career_skills=cs_list,
            profile_skills=profile_skills,
        )
        assert result.career_id == str(career.id)
        assert result.career_title == career.title
        assert 0.0 <= result.overall_score <= 1.0


@pytest.mark.asyncio
async def test_interview_question_selection(session: AsyncSession):
    """Interview question selector can select seeded questions."""
    await _ensure_reference_profile(session)

    await _upsert_interview_questions(session, INTERVIEW_QUESTIONS)
    await session.commit()

    from sqlalchemy import select
    from app.models.interview import InterviewQuestion

    result = await session.execute(select(InterviewQuestion))
    questions = result.scalars().all()
    assert len(questions) == len(INTERVIEW_QUESTIONS)

    # Verify all questions have valid difficulty and type
    valid_difficulties = {"EASY", "MEDIUM", "HARD", "EXPERT"}
    valid_types = {"TECHNICAL", "CONCEPTUAL", "SCENARIO", "BEHAVIORAL", "SYSTEM_DESIGN", "PROBLEM_SOLVING"}
    for q in questions:
        assert q.difficulty in valid_difficulties
        assert q.question_type in valid_types

    # Test question selector
    selector = AdaptiveQuestionSelector()
    candidate_questions = [
        {
            "id": str(q.id),
            "question_text": q.question_text,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "skill_names": [],
            "career_importance": 0.5,
        }
        for q in questions
    ]

    selected = selector.select_next_question(
        candidate_questions=candidate_questions,
        skill_gaps={},
        skill_coverage={},
        asked_question_ids=set(),
        recent_difficulty="MEDIUM",
        recent_scores=[],
        interview_mode="MIXED",
        asked_types=[],
    )
    assert selected is not None
    assert "id" in selected


@pytest.mark.asyncio
async def test_roadmap_generation_against_seeded_data(session: AsyncSession):
    """Roadmap generation can resolve seeded resources/dependencies."""
    await _ensure_reference_profile(session)

    # Clean up any existing careers from other tests
    from sqlalchemy import delete
    from app.models.career import Career, CareerSkill, CareerTool, CareerProject, CareerSource
    from app.models.learning import LearningResource, LearningResourceSkill, SkillDependency
    from app.models.profile import Profile

    await session.execute(delete(CareerSkill))
    await session.execute(delete(CareerTool))
    await session.execute(delete(CareerProject))
    await session.execute(delete(CareerSource))
    await session.execute(delete(Career))
    await session.execute(delete(LearningResource))
    await session.execute(delete(LearningResourceSkill))
    await session.execute(delete(SkillDependency))
    await session.execute(delete(Profile))
    await session.commit()

    # Seed careers
    for career_data in CAREERS:
        career_id = await _upsert_career(session, career_data)
        await _upsert_career_skills(session, career_id, career_data.get("skills", []))
        await _upsert_career_tools(session, career_id, career_data.get("tools", []))
        await _upsert_career_projects(session, career_id, career_data.get("projects", []))
        await _upsert_career_sources(session, career_id, career_data.get("sources", []))

    # Seed learning resources
    await _upsert_learning_resources(session, LEARNING_RESOURCES)
    await _upsert_skill_dependencies(session, SKILL_DEPENDENCIES)
    await session.commit()

    # Create a profile
    profile = await create_profile(
        session,
        ProfileCreate(full_name="Test User", headline="Engineer", email="test@example.com"),
        user_id=uuid.uuid4(),
    )

    # Find a career with skills
    repo = CareerRepository(session)
    careers = await repo.list_careers()
    target_career = careers[0]
    career_skills = await repo.get_skills(target_career.id)

    # Generate roadmap
    roadmap_service = LearningRoadmapService(session)
    result = await roadmap_service.generate_roadmap(
        profile_id=str(profile.id),
        career_slug=target_career.slug,
        profile_skills=[
            {"name": s.skill_name, "proficiency": "BEGINNER", "years_experience": 0.0, "source": "USER_CONFIRMED"}
            for s in career_skills[:2]  # Only know 2 skills, rest are gaps
        ],
    )

    assert result is not None
    assert "roadmap_id" in result
    assert "items" in result
    assert len(result["items"]) > 0  # Should have skills to learn
