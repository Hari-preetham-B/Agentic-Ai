"""Tests for the agent runs API endpoints."""

import uuid

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.auth.provider import FakeAuthProvider
from app.core.auth.dependency import set_auth_provider
from app.core.database import get_engine
from app.main import app
from app.models.career import Career, CareerSkill
from app.models.profile import CareerGoal, Education, Experience, Profile, Skill

USER_ID = "33333333-3333-4333-8333-333333333333"
AUTH_HEADERS = {"Authorization": f"Bearer fake:{USER_ID}:test@example.com"}


@pytest.fixture
async def client() -> AsyncClient:
    set_auth_provider(FakeAuthProvider())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_agent_runs_endpoints(client: AsyncClient) -> None:
    # Seed a profile and career data so career_analysis can run end-to-end.
    # Use upsert (idempotent by slug) so the test is safe to re-run in a shared SQLite session.
    engine = get_engine()
    factory = async_sessionmaker(engine, expire_on_commit=False)

    profile_id = uuid.uuid4()
    async with factory() as sess:
        # Upsert career by slug so this test is idempotent in a shared DB.
        existing_career = await sess.execute(
            select(Career).where(Career.slug == "software-engineer")
        )
        career = existing_career.scalar_one_or_none()
        if career is None:
            career = Career(
                id=uuid.uuid4(),
                slug="software-engineer",
                title="Software Engineer",
                domain="Software Development",
                summary="Designs, builds, tests, and maintains software applications.",
                description="Software engineer career profile.",
            )
            sess.add(career)
            await sess.flush()
        else:
            # Reuse existing career ID; ensure skills are also present below.
            pass

        sess.add(
            Profile(
                id=profile_id,
                user_id=uuid.UUID(USER_ID),
                full_name="Test User",
                headline="Software Engineer",
                email="test@example.com",
                profile_status="CONFIRMED",
            )
        )
        sess.add(
            Skill(
                profile_id=profile_id,
                name="Python",
                category="Programming Language",
                proficiency="ADVANCED",
                source="USER_CONFIRMED",
            )
        )
        sess.add(
            Skill(
                profile_id=profile_id,
                name="SQL",
                category="Database",
                proficiency="INTERMEDIATE",
                source="USER_CONFIRMED",
            )
        )

        # Ensure CareerSkills for Python and SQL exist on this career.
        # Use importlib.util.find_spec to avoid importing SQLAlchemy models
        # at module load time if needed, but here we import directly.
        career_skills_result = await sess.execute(
            select(CareerSkill).where(CareerSkill.career_id == career.id)
        )
        existing_skills = {cs.skill_name: cs for cs in career_skills_result.scalars().all()}

        for skill_name, skill_data in [("Python", {"category": "Programming Language", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Core programming language."}),
                                     ("SQL", {"category": "Database", "importance": "CORE", "minimum_level": "INTERMEDIATE", "description": "Database query language."})]:
            if skill_name not in existing_skills:
                sess.add(
                    CareerSkill(
                        career_id=career.id,
                        skill_name=skill_name,
                        category=skill_data["category"],
                        importance=skill_data["importance"],
                        minimum_level=skill_data["minimum_level"],
                        description=skill_data["description"],
                    )
                )
        await sess.commit()

    # POST /agent-runs with career_analysis capability
    resp = await client.post(
        "/agent-runs",
        headers=AUTH_HEADERS,
        json={
            "profile_id": str(profile_id),
            "capability": "career_analysis",
            "input": "software-engineer",
        },
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "COMPLETED"
    assert body["agent"] == "career_agent"
    assert body["run_id"]
    assert body["result"] is not None
    assert body["error"] is None

    run_id = body["run_id"]

    # GET /agent-runs/{run_id}
    resp = await client.get(f"/agent-runs/{run_id}", headers=AUTH_HEADERS)
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == run_id
    assert detail["capability"] == "career_analysis"
    assert detail["status"] == "COMPLETED"
    assert len(detail["events"]) >= 1
    assert any(e["event_type"] == "RUN_STARTED" for e in detail["events"])

    # GET /agent-runs/{run_id}/events
    resp = await client.get(
        f"/agent-runs/{run_id}/events", headers=AUTH_HEADERS
    )
    assert resp.status_code == 200, resp.text
    events = resp.json()
    assert isinstance(events, list)
    assert len(events) >= 1
    seqs = [e["sequence"] for e in events]
    assert seqs == sorted(seqs)
    # safe payloads - no chain of thought
    for e in events:
        payload_str = str(e.get("payload"))
        assert "chain-of-thought" not in payload_str.lower()
        assert "internal reasoning" not in payload_str.lower()


@pytest.mark.anyio
async def test_profile_summary_with_unowned_profile_is_rejected(
    client: AsyncClient,
) -> None:
    resp = await client.post(
        "/agent-runs",
        headers=AUTH_HEADERS,
        json={
            "profile_id": "00000000-0000-0000-0000-000000000001",
            "capability": "profile_summary",
            "input": "Summarize my current profile.",
        },
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.anyio
async def test_agent_runs_unsupported_capability(client: AsyncClient) -> None:
    resp = await client.post(
        "/agent-runs",
        headers=AUTH_HEADERS,
        json={
            "capability": "not_a_real_capability",
            "input": "x",
        },
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert "Unsupported capability" in body["error"]


@pytest.mark.anyio
async def test_agent_run_not_found(client: AsyncClient) -> None:
    resp = await client.get(
        "/agent-runs/00000000-0000-0000-0000-000000000999",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404

    resp = await client.get(
        "/agent-runs/00000000-0000-0000-0000-000000000999/events",
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_agent_runs_require_authentication(client: AsyncClient) -> None:
    resp = await client.post(
        "/agent-runs",
        json={
            "profile_id": "00000000-0000-0000-0000-000000000001",
            "capability": "profile_summary",
            "input": "x",
        },
    )
    assert resp.status_code == 401

    resp = await client.get("/agent-runs")
    assert resp.status_code == 401
