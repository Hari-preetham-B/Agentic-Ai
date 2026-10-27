"""Tests for career knowledge models, seeding, and retrieval."""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_engine_for_testing
from app.models.career import Career, CareerProject, CareerSkill, CareerSource, CareerTool
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.repositories import CareerRepository


@pytest_asyncio.fixture
async def seeded_career(session: AsyncSession) -> str:
    """Seed a career with skills, tools, projects, and sources. Return its ID."""
    career_id = uuid.uuid4()
    slug = f"test-engineer-{uuid.uuid4().hex[:8]}"
    career = Career(
        id=career_id,
        slug=slug,
        title="Test Engineer",
        domain="Engineering",
        summary="A test career.",
        description="A test career description.",
        education_expectations={"typical": "Bachelor's degree"},
        experience_expectations={"entry_level": "0-2 years"},
    )
    session.add(career)
    session.add(
        CareerSkill(
            career_id=career_id,
            skill_name="Python",
            category="Programming Language",
            importance="CORE",
            minimum_level="INTERMEDIATE",
            description="Core programming language.",
        )
    )
    session.add(
        CareerSkill(
            career_id=career_id,
            skill_name="SQL",
            category="Database",
            importance="IMPORTANT",
            minimum_level="BEGINNER",
            description="Database query language.",
        )
    )
    session.add(
        CareerTool(
            career_id=career_id,
            tool_name="Git",
            category="Version Control",
            importance="CORE",
        )
    )
    session.add(
        CareerProject(
            career_id=career_id,
            project_type="Capstone",
            description="Build a test project.",
            skills_demonstrated=["Python", "SQL"],
            difficulty="Intermediate",
        )
    )
    session.add(
        CareerSource(
            career_id=career_id,
            title="Test Source",
            publisher="Test Publisher",
            url="https://example.com",
            source_type="government",
            reliability="high",
        )
    )
    await session.commit()
    return str(career_id)


@pytest.mark.asyncio
async def test_career_retrieval_by_slug(session: AsyncSession, seeded_career: str) -> None:
    """Test retrieving a career by slug."""
    service = CareerKnowledgeService(session)
    # Get the slug from the seeded career by querying
    repo = CareerRepository(session)
    careers = await repo.list_careers()
    seeded = [c for c in careers if c.id == uuid.UUID(seeded_career)]
    assert len(seeded) == 1
    slug = seeded[0].slug
    
    career = await service.get_career(slug)
    assert career is not None
    assert career["slug"] == slug
    assert career["title"] == "Test Engineer"
    assert career["domain"] == "Engineering"
    assert len(career["skills"]) == 2
    assert career["skills"][0]["skill_name"] == "Python"
    assert len(career["tools"]) == 1
    assert career["tools"][0]["tool_name"] == "Git"
    assert len(career["projects"]) == 1
    assert len(career["sources"]) == 1


@pytest.mark.asyncio
async def test_career_retrieval_not_found(session: AsyncSession) -> None:
    """Test retrieving a non-existent career."""
    service = CareerKnowledgeService(session)
    career = await service.get_career("non-existent-slug")
    assert career is None


@pytest.mark.asyncio
async def test_career_requirements_retrieval(session: AsyncSession, seeded_career: str) -> None:
    """Test retrieving career requirements."""
    service = CareerKnowledgeService(session)
    repo = CareerRepository(session)
    careers = await repo.list_careers()
    seeded = [c for c in careers if c.id == uuid.UUID(seeded_career)]
    assert len(seeded) == 1
    slug = seeded[0].slug
    
    reqs = await service.get_career_requirements(slug)
    assert reqs is not None
    assert reqs["career_id"] == seeded_career
    assert reqs["title"] == "Test Engineer"
    assert len(reqs["skills"]) == 2
    assert len(reqs["tools"]) == 1
    assert len(reqs["projects"]) == 1
    assert len(reqs["sources"]) == 1


@pytest.mark.asyncio
async def test_career_skills_retrieval(session: AsyncSession, seeded_career: str) -> None:
    """Test retrieving career skills."""
    service = CareerKnowledgeService(session)
    repo = CareerRepository(session)
    careers = await repo.list_careers()
    seeded = [c for c in careers if c.id == uuid.UUID(seeded_career)]
    assert len(seeded) == 1
    slug = seeded[0].slug
    
    skills = await service.get_career_skills(slug)
    assert skills is not None
    assert len(skills) == 2
    python_skills = [s for s in skills if s["skill_name"] == "Python"]
    assert len(python_skills) == 1
    assert python_skills[0]["importance"] == "CORE"


@pytest.mark.asyncio
async def test_career_repository_list(session: AsyncSession, seeded_career: str) -> None:
    """Test listing all careers."""
    repo = CareerRepository(session)
    careers = await repo.list_careers()
    assert len(careers) >= 1
    seeded = [c for c in careers if c.id == uuid.UUID(seeded_career)]
    assert len(seeded) == 1
    assert seeded[0].slug.startswith("test-engineer-")


@pytest.mark.asyncio
async def test_career_repository_get_by_id(session: AsyncSession, seeded_career: str) -> None:
    """Test retrieving a career by ID."""
    repo = CareerRepository(session)
    career = await repo.get_by_id(uuid.UUID(seeded_career))
    assert career is not None
    assert career.title == "Test Engineer"
    assert career.slug.startswith("test-engineer-")


@pytest.mark.asyncio
async def test_skill_importance_values(session: AsyncSession, seeded_career: str) -> None:
    """Test that skill importance values are valid."""
    repo = CareerRepository(session)
    careers = await repo.list_careers()

    valid_importances = {"CORE", "IMPORTANT", "SUPPORTING"}
    for career in careers:
        skills = await repo.get_skills(career.id)
        for skill in skills:
            assert skill.importance in valid_importances, (
                f"Invalid importance {skill.importance} for {skill.skill_name}"
            )


__all__ = [
    "test_career_retrieval_by_slug",
    "test_career_retrieval_not_found",
    "test_career_requirements_retrieval",
    "test_career_skills_retrieval",
    "test_career_repository_list",
    "test_career_repository_get_by_id",
    "test_skill_importance_values",
]
