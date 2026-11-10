"""Deterministic reference data seed command.

Usage:
    python -m app.scripts.seed_reference_data

Behavior:
1. Connects using the configured DATABASE_URL
2. Verifies the schema is at the expected Alembic head
3. Seeds reference entities (careers, skills, tools, projects, sources,
   learning resources, skill dependencies, interview questions)
4. Commits atomically
5. Reports counts
6. Exits non-zero on failure
7. Safe to rerun (idempotent upserts based on stable identifiers)

Does NOT touch user-owned data. Does NOT delete existing reference data.
Uses upsert/update behavior based on stable identifiers (career slug,
skill name, resource title+provider, question text).

A single "reference" profile (user_id=NULL) owns all reference skills so
that the Skill model's NOT NULL profile_id constraint is satisfied while
keeping reference skills separate from user data.
"""

from __future__ import annotations

import asyncio
import sys
import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.career import (
    Career,
    CareerProject,
    CareerSkill,
    CareerSource,
    CareerTool,
)
from app.models.interview import InterviewQuestion, InterviewQuestionSkill
from app.models.learning import (
    LearningResource,
    LearningResourceSkill,
    SkillDependency,
)
from app.models.profile import Profile, Skill
from app.scripts.seed_data import CAREERS, INTERVIEW_QUESTIONS, LEARNING_RESOURCES, SKILL_DEPENDENCIES

EXPECTED_ALEMBIC_HEAD = "0006_row_level_security"

# A stable UUID for the reference profile that owns all reference skills.
# This is NOT a real user — it's a namespace for curated reference data.
REFERENCE_PROFILE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _ensure_reference_profile(session: AsyncSession) -> uuid.UUID:
    """Create or return the reference profile that owns reference skills."""
    result = await session.execute(select(Profile).where(Profile.id == REFERENCE_PROFILE_ID))
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = Profile(
            id=REFERENCE_PROFILE_ID,
            user_id=None,
            full_name="Reference Data",
            headline="Curated reference data namespace",
            email=None,
            profile_status="CONFIRMED",
        )
        session.add(profile)
        await session.flush()
    return profile.id


async def check_alembic_head(session: AsyncSession) -> str:
    """Return the current Alembic version, or raise if not at expected head."""
    result = await session.execute(text("SELECT version_num FROM alembic_version"))
    row = result.fetchone()
    if row is None:
        raise RuntimeError("alembic_version table is empty — migrations may not have been applied")
    current = row[0]
    if current != EXPECTED_ALEMBIC_HEAD:
        raise RuntimeError(
            f"Database is at Alembic version '{current}', expected '{EXPECTED_ALEMBIC_HEAD}'. "
            "Run 'alembic upgrade head' before seeding."
        )
    return current


async def _upsert_career(session: AsyncSession, data: dict[str, Any]) -> uuid.UUID:
    """Insert or update a career by slug. Returns the career ID."""
    slug = data["slug"]
    result = await session.execute(select(Career).where(Career.slug == slug))
    career = result.scalar_one_or_none()

    if career is None:
        career = Career(
            id=uuid.uuid4(),
            slug=slug,
            title=data["title"],
            domain=data["domain"],
            summary=data.get("summary"),
            description=data.get("description"),
            education_expectations=data.get("education_expectations"),
            experience_expectations=data.get("experience_expectations"),
        )
        session.add(career)
        await session.flush()
    else:
        career.title = data["title"]
        career.domain = data["domain"]
        career.summary = data.get("summary")
        career.description = data.get("description")
        career.education_expectations = data.get("education_expectations")
        career.experience_expectations = data.get("experience_expectations")

    return career.id


async def _upsert_career_skills(
    session: AsyncSession, career_id: uuid.UUID, skills: list[dict[str, Any]]
) -> int:
    """Upsert career skills keyed by (career_id, skill_name). Returns count."""
    count = 0
    for s in skills:
        result = await session.execute(
            select(CareerSkill).where(
                CareerSkill.career_id == career_id,
                CareerSkill.skill_name == s["skill_name"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            session.add(
                CareerSkill(
                    id=uuid.uuid4(),
                    career_id=career_id,
                    skill_name=s["skill_name"],
                    category=s.get("category"),
                    importance=s["importance"],
                    minimum_level=s.get("minimum_level"),
                    description=s.get("description"),
                )
            )
            count += 1
        else:
            existing.category = s.get("category")
            existing.importance = s["importance"]
            existing.minimum_level = s.get("minimum_level")
            existing.description = s.get("description")
            count += 1
    return count


async def _upsert_career_tools(
    session: AsyncSession, career_id: uuid.UUID, tools: list[dict[str, Any]]
) -> int:
    """Upsert career tools keyed by (career_id, tool_name). Returns count."""
    count = 0
    for t in tools:
        result = await session.execute(
            select(CareerTool).where(
                CareerTool.career_id == career_id,
                CareerTool.tool_name == t["tool_name"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            session.add(
                CareerTool(
                    id=uuid.uuid4(),
                    career_id=career_id,
                    tool_name=t["tool_name"],
                    category=t.get("category"),
                    importance=t["importance"],
                )
            )
            count += 1
        else:
            existing.category = t.get("category")
            existing.importance = t["importance"]
            count += 1
    return count


async def _upsert_career_projects(
    session: AsyncSession, career_id: uuid.UUID, projects: list[dict[str, Any]]
) -> int:
    """Upsert career projects keyed by (career_id, project_type, description)."""
    count = 0
    for p in projects:
        result = await session.execute(
            select(CareerProject).where(
                CareerProject.career_id == career_id,
                CareerProject.project_type == p["project_type"],
                CareerProject.description == p["description"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            session.add(
                CareerProject(
                    id=uuid.uuid4(),
                    career_id=career_id,
                    project_type=p["project_type"],
                    description=p["description"],
                    skills_demonstrated=p.get("skills_demonstrated"),
                    difficulty=p.get("difficulty"),
                )
            )
            count += 1
        else:
            existing.skills_demonstrated = p.get("skills_demonstrated")
            existing.difficulty = p.get("difficulty")
            count += 1
    return count


async def _upsert_career_sources(
    session: AsyncSession, career_id: uuid.UUID, sources: list[dict[str, Any]]
) -> int:
    """Upsert career sources keyed by (career_id, title, publisher)."""
    count = 0
    for s in sources:
        result = await session.execute(
            select(CareerSource).where(
                CareerSource.career_id == career_id,
                CareerSource.title == s["title"],
                CareerSource.publisher == s["publisher"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            session.add(
                CareerSource(
                    id=uuid.uuid4(),
                    career_id=career_id,
                    title=s["title"],
                    publisher=s["publisher"],
                    url=s.get("url"),
                    source_type=s["source_type"],
                    reliability=s["reliability"],
                )
            )
            count += 1
        else:
            existing.url = s.get("url")
            existing.source_type = s["source_type"]
            existing.reliability = s["reliability"]
            count += 1
    return count


async def _get_or_create_reference_skill(
    session: AsyncSession, skill_name: str
) -> uuid.UUID:
    """Get or create a reference Skill owned by the reference profile.

    Returns the skill ID. Uses the reference profile so the NOT NULL
    profile_id constraint is satisfied without tying the skill to a real user.
    """
    result = await session.execute(
        select(Skill).where(
            Skill.profile_id == REFERENCE_PROFILE_ID,
            Skill.name == skill_name,
        )
    )
    skill = result.scalar_one_or_none()
    if skill is None:
        skill = Skill(
            id=uuid.uuid4(),
            profile_id=REFERENCE_PROFILE_ID,
            name=skill_name,
            source="SYSTEM_INFERRED",
        )
        session.add(skill)
        await session.flush()
    return skill.id


async def _upsert_learning_resources(
    session: AsyncSession, resources: list[dict[str, Any]]
) -> int:
    """Upsert learning resources keyed by (title, provider). Returns count."""
    count = 0
    for r in resources:
        result = await session.execute(
            select(LearningResource).where(
                LearningResource.title == r["title"],
                LearningResource.provider == r["provider"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            resource = LearningResource(
                id=uuid.uuid4(),
                title=r["title"],
                provider=r["provider"],
                resource_type=r["resource_type"],
                url=r.get("url"),
                description=r.get("description"),
                difficulty=r.get("difficulty"),
                estimated_hours=r.get("estimated_hours"),
                metadata_={"source": "seed_reference_data"},
            )
            session.add(resource)
            await session.flush()
            resource_id = resource.id
        else:
            resource_id = existing.id
            existing.resource_type = r["resource_type"]
            existing.url = r.get("url")
            existing.description = r.get("description")
            existing.difficulty = r.get("difficulty")
            existing.estimated_hours = r.get("estimated_hours")

        # Upsert skill mappings
        for mapping in r.get("skill_mappings", []):
            result = await session.execute(
                select(LearningResourceSkill).where(
                    LearningResourceSkill.resource_id == resource_id,
                    LearningResourceSkill.skill_name == mapping["skill_name"],
                )
            )
            existing_mapping = result.scalar_one_or_none()
            if existing_mapping is None:
                session.add(
                    LearningResourceSkill(
                        id=uuid.uuid4(),
                        resource_id=resource_id,
                        skill_name=mapping["skill_name"],
                        relevance_score=mapping.get("relevance_score", 0.5),
                        coverage_type=mapping.get("coverage_type"),
                    )
                )
            else:
                existing_mapping.relevance_score = mapping.get(
                    "relevance_score", 0.5
                )
                existing_mapping.coverage_type = mapping.get("coverage_type")
        count += 1
    return count


async def _upsert_skill_dependencies(
    session: AsyncSession, deps: list[dict[str, Any]]
) -> int:
    """Upsert skill dependencies keyed by (skill, prerequisite). Returns count."""
    count = 0
    for d in deps:
        skill_id = await _get_or_create_reference_skill(session, d["skill"])
        prereq_id = await _get_or_create_reference_skill(session, d["prerequisite_skill"])

        result = await session.execute(
            select(SkillDependency).where(
                SkillDependency.skill_id == skill_id,
                SkillDependency.prerequisite_skill_id == prereq_id,
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            session.add(
                SkillDependency(
                    id=uuid.uuid4(),
                    skill_id=skill_id,
                    prerequisite_skill_id=prereq_id,
                    strength=d.get("strength", "REQUIRED"),
                    source_reference=d.get("source_reference"),
                )
            )
        else:
            existing.strength = d.get("strength", "REQUIRED")
            existing.source_reference = d.get("source_reference")
        count += 1
    return count


async def _upsert_interview_questions(
    session: AsyncSession, questions: list[dict[str, Any]]
) -> int:
    """Upsert interview questions keyed by question_text. Returns count."""
    count = 0
    for q in questions:
        result = await session.execute(
            select(InterviewQuestion).where(
                InterviewQuestion.question_text == q["question_text"]
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            question = InterviewQuestion(
                id=uuid.uuid4(),
                career_id=None,  # reference question, not tied to a specific career
                question_text=q["question_text"],
                question_type=q["question_type"],
                difficulty=q["difficulty"],
                source=q.get("source", "CURATED"),
                expected_competency=q.get("expected_competency"),
                metadata_={"source": "seed_reference_data"},
            )
            session.add(question)
            await session.flush()
            question_id = question.id
        else:
            question_id = existing.id
            existing.question_type = q["question_type"]
            existing.difficulty = q["difficulty"]
            existing.source = q.get("source", "CURATED")
            existing.expected_competency = q.get("expected_competency")

        # Upsert skill mappings (skill_name is a string, not FK to skills)
        for mapping in q.get("skill_mappings", []):
            result = await session.execute(
                select(InterviewQuestionSkill).where(
                    InterviewQuestionSkill.question_id == question_id,
                    InterviewQuestionSkill.skill_name == mapping["skill_name"],
                )
            )
            existing_mapping = result.scalar_one_or_none()
            if existing_mapping is None:
                session.add(
                    InterviewQuestionSkill(
                        id=uuid.uuid4(),
                        question_id=question_id,
                        skill_name=mapping["skill_name"],
                        relevance_score=mapping.get("relevance_score", 0.5),
                    )
                )
            else:
                existing_mapping.relevance_score = mapping.get(
                    "relevance_score", 0.5
                )
        count += 1
    return count


async def seed_reference_data() -> dict[str, int]:
    """Run the full seed operation. Returns a dict of table -> count."""
    settings = get_settings()
    database_url = settings.database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured — cannot seed reference data")

    from app.core.database import engine_kwargs

    engine = create_async_engine(database_url, **engine_kwargs(database_url))
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    counts: dict[str, int] = {}

    try:
        async with factory() as session:
            # 1. Verify Alembic head
            await check_alembic_head(session)

            # 2. Ensure reference profile exists
            await _ensure_reference_profile(session)

            # 3. Seed careers and their children
            career_count = 0
            for career_data in CAREERS:
                career_id = await _upsert_career(session, career_data)
                career_count += 1
                await _upsert_career_skills(
                    session, career_id, career_data.get("skills", [])
                )
                await _upsert_career_tools(
                    session, career_id, career_data.get("tools", [])
                )
                await _upsert_career_projects(
                    session, career_id, career_data.get("projects", [])
                )
                await _upsert_career_sources(
                    session, career_id, career_data.get("sources", [])
                )
            counts["careers"] = career_count

            # Count career children
            result = await session.execute(select(CareerSkill))
            counts["career_skills"] = len(result.scalars().all())
            result = await session.execute(select(CareerTool))
            counts["career_tools"] = len(result.scalars().all())
            result = await session.execute(select(CareerProject))
            counts["career_projects"] = len(result.scalars().all())
            result = await session.execute(select(CareerSource))
            counts["career_sources"] = len(result.scalars().all())

            # 4. Seed learning resources
            counts["learning_resources"] = await _upsert_learning_resources(
                session, LEARNING_RESOURCES
            )
            result = await session.execute(select(LearningResourceSkill))
            counts["learning_resource_skills"] = len(result.scalars().all())

            # 5. Seed skill dependencies
            counts["skill_dependencies"] = await _upsert_skill_dependencies(
                session, SKILL_DEPENDENCIES
            )

            # 6. Seed interview questions
            counts["interview_questions"] = await _upsert_interview_questions(
                session, INTERVIEW_QUESTIONS
            )
            result = await session.execute(select(InterviewQuestionSkill))
            counts["interview_question_skills"] = len(result.scalars().all())

            await session.commit()

    finally:
        await engine.dispose()

    return counts


def main() -> None:
    """Entry point for `python -m app.scripts.seed_reference_data`."""
    try:
        counts = asyncio.run(seed_reference_data())
    except Exception as exc:
        print(f"SEED FAILED: {exc}", file=sys.stderr)
        sys.exit(1)

    print("Reference data seed complete.")
    print("=" * 40)
    for table, count in sorted(counts.items()):
        print(f"  {table}: {count}")
    print("=" * 40)
    print("Seed operation is idempotent — safe to rerun.")


if __name__ == "__main__":
    main()
