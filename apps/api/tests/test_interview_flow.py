"""Integration tests for the adaptive interview question/answer API."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.auth.dependency import set_auth_provider
from app.core.auth.provider import FakeAuthProvider
from app.core.database import Base, get_engine
from app.main import app
from app.models.career import Career, CareerSkill
from app.models.interview import InterviewQuestion, InterviewQuestionSkill
from app.models.profile import Profile, Skill

USER_ID = "11111111-1111-4111-8111-111111111111"
OTHER_USER_ID = "22222222-2222-4222-8222-222222222222"
HEADERS = {"Authorization": f"Bearer fake:{USER_ID}:interview@example.com"}


@pytest.fixture
async def client() -> AsyncClient:
    set_auth_provider(FakeAuthProvider())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _seed() -> tuple[uuid.UUID, uuid.UUID]:
    engine = get_engine()
    # Other test modules can replace the global engine with a fresh in-memory
    # database. Ensure the schema exists before seeding.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    profile_id = uuid.uuid4()
    career_id = uuid.uuid4()
    async with factory() as sess:
        sess.add(
            Profile(
                id=profile_id,
                user_id=uuid.UUID(USER_ID),
                full_name="Interview Candidate",
                email="interview@example.com",
                profile_status="CONFIRMED",
            )
        )
        sess.add(
            Skill(
                profile_id=profile_id,
                name="Python",
                proficiency="INTERMEDIATE",
                source="USER_CONFIRMED",
            )
        )
        sess.add(
            Career(
                id=career_id,
                slug=f"test-career-{career_id.hex[:8]}",
                title="Test Software Engineer",
                domain="Engineering",
            )
        )
        sess.add(
            CareerSkill(
                career_id=career_id,
                skill_name="Python",
                importance="CORE",
                minimum_level="ADVANCED",
            )
        )
        for index in range(2):
            question = InterviewQuestion(
                id=uuid.uuid4(),
                career_id=career_id,
                question_text=(
                    f"How would you use Python to solve problem {index}, "
                    "and what trade-offs would you consider?"
                ),
                question_type="TECHNICAL",
                difficulty="MEDIUM",
            )
            sess.add(question)
            sess.add(
                InterviewQuestionSkill(
                    question_id=question.id,
                    skill_name="Python",
                    relevance_score=0.9,
                )
            )
        await sess.commit()
    return profile_id, career_id


@pytest.mark.anyio
async def test_adaptive_interview_flow(client: AsyncClient) -> None:
    profile_id, career_id = await _seed()

    # Unauthenticated access is rejected.
    resp = await client.post(
        "/interviews",
        json={"profile_id": str(profile_id), "career_id": str(career_id)},
    )
    assert resp.status_code == 401

    created = await client.post(
        "/interviews",
        headers=HEADERS,
        json={
            "profile_id": str(profile_id),
            "career_id": str(career_id),
            "mode": "MIXED",
            "difficulty": "MEDIUM",
            "target_question_count": 2,
        },
    )
    assert created.status_code == 200, created.text
    session_id = created.json()["session_id"]

    started = await client.post(f"/interviews/{session_id}/start", headers=HEADERS)
    assert started.status_code == 200, started.text
    assert started.json()["status"] == "ACTIVE"

    answered = 0
    for _ in range(2):
        question = await client.get(f"/interviews/{session_id}/next", headers=HEADERS)
        assert question.status_code == 200, question.text
        payload = question.json()
        assert payload["no_more_questions"] is False
        assert payload["question_text"]

        answer = await client.post(
            f"/interviews/{session_id}/answers",
            headers=HEADERS,
            json={
                "question_id": payload["question_id"],
                "answer_text": (
                    "First, I would use Python because its standard library "
                    "makes the implementation straightforward. For example, "
                    "I would write tests, measure performance, and consider "
                    "the trade-off between readability and speed. The result "
                    "would be a maintainable solution with clear error handling."
                ),
            },
        )
        assert answer.status_code == 200, answer.text
        body = answer.json()
        assert body["evaluation_status"] == "EVALUATED"
        assert body["score"] is not None and body["score"] > 0
        assert body["evaluator"] in (
            "deterministic_heuristic",
            "deterministic_fallback",
        ) or body["evaluator"].startswith("llm:")
        answered += 1

    assert answered == 2

    exhausted = await client.get(f"/interviews/{session_id}/next", headers=HEADERS)
    assert exhausted.status_code == 200
    assert exhausted.json()["no_more_questions"] is True

    completed = await client.post(f"/interviews/{session_id}/complete", headers=HEADERS)
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"

    results = await client.get(f"/interviews/{session_id}/results", headers=HEADERS)
    assert results.status_code == 200, results.text
    body = results.json()
    assert body["questions_attempted"] == 2
    assert body["overall_score"] > 0
    assert any(s["skill_name"] == "Python" for s in body["skill_performance"])

    sessions = await client.get(
        f"/interviews?profile_id={profile_id}", headers=HEADERS
    )
    assert sessions.status_code == 200
    assert len(sessions.json()) >= 1


@pytest.mark.anyio
async def test_interview_session_is_isolated_between_users(
    client: AsyncClient,
) -> None:
    profile_id, career_id = await _seed()
    created = await client.post(
        "/interviews",
        headers=HEADERS,
        json={"profile_id": str(profile_id), "career_id": str(career_id)},
    )
    session_id = created.json()["session_id"]

    other = {
        "Authorization": f"Bearer fake:{OTHER_USER_ID}:other@example.com"
    }
    resp = await client.get(f"/interviews/{session_id}", headers=other)
    assert resp.status_code == 404

    resp = await client.get(f"/interviews?profile_id={profile_id}", headers=other)
    assert resp.status_code == 404
