"""Tests for the Application Orchestrator."""

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, set_engine_for_testing
from app.models.profile import Profile
from app.core.llm import FakeLLMProvider
from app.services.orchestrator import AgentOrchestrator
from app.workflows.agent_workflow import AgentWorkflow
from app.services.trace import TraceService


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:?cache=shared", echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_engine_for_testing(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        profile = Profile(
            full_name="Ada Lovelace",
            headline="Student",
            email="ada@example.com",
            profile_status="DRAFT",
        )
        session.add(profile)
        await session.flush()
        await session.refresh(profile)
        session.profile_id = profile.id  # type: ignore[attr-defined]
        yield session
    await engine.dispose()


def make_orchestrator(session: AsyncSession) -> AgentOrchestrator:
    return AgentOrchestrator(
        session=session,
        trace_service=TraceService(session),
        llm_provider=FakeLLMProvider(),
        workflow=AgentWorkflow(trace_service=TraceService(session)),
    )


@pytest.mark.asyncio
async def test_supported_capabilities_listed() -> None:
    caps = AgentOrchestrator.supported_capabilities()
    assert "profile_summary" in caps
    assert "career_analysis" in caps
    assert "skill_gap" in caps
    assert "learning_plan" in caps
    assert "interview" in caps
    assert "evidence_check" in caps


@pytest.mark.asyncio
async def test_unsupported_capability_rejected() -> None:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:?cache=shared", echo=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    set_engine_for_testing(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        # Seed a profile so profile_id is valid.
        profile = Profile(
            full_name="Ada Lovelace",
            headline="Student",
            email="ada@example.com",
            profile_status="DRAFT",
        )
        session.add(profile)
        await session.flush()
        await session.refresh(profile)
        session.profile_id = profile.id  # type: ignore[attr-defined]
        orch = make_orchestrator(session)
        result = await orch.run_capability(
            capability="not_a_real_capability",
            profile_id=str(session.profile_id),  # type: ignore[attr-defined]
            user_input="x",
        )
        assert result["status"] == "FAILED"
        assert "Unsupported capability" in result["error"]
    await engine.dispose()


@pytest.mark.asyncio
async def test_profile_summary_end_to_end(db_session: AsyncSession) -> None:
    profile_id = str(db_session.profile_id)  # type: ignore[attr-defined]
    orch = make_orchestrator(db_session)

    result = await orch.run_capability(
        capability="profile_summary",
        profile_id=profile_id,
        user_input="Summarize my current profile.",
    )

    assert result["status"] == "COMPLETED"
    assert result["agent"] == "profile_agent"
    assert result["run_id"]
    assert result["result"] is not None
    assert result["result"]["profile_id"] == profile_id
    assert isinstance(result["result"]["overview"], str)
    assert result["error"] is None


@pytest.mark.asyncio
async def test_run_creation_and_trace_recorded(db_session: AsyncSession) -> None:
    profile_id = str(db_session.profile_id)  # type: ignore[attr-defined]
    orch = make_orchestrator(db_session)

    result = await orch.run_capability(
        capability="profile_summary",
        profile_id=profile_id,
        user_input="hi",
    )

    assert result["status"] == "COMPLETED"
    run_id = result["run_id"]

    # Fetch run + events from trace.
    run = await orch.trace.run_repo.get(__import__("uuid", fromlist=["UUID"]).UUID(run_id))  # noqa: E501
    assert run is not None
    assert run.capability == "profile_summary"
    assert run.status == "COMPLETED"
    assert run.provider == "fake"

    events = await orch.trace.event_repo.list_for_run(run.id)
    event_types = [e.event_type for e in events]
    assert "RUN_STARTED" in event_types
    assert "RUN_COMPLETED" in event_types
    assert any(et.startswith("AGENT") for et in event_types)
    assert any(et.startswith("TOOL") for et in event_types)


@pytest.mark.asyncio
async def test_nonexistent_profile_fails_gracefully(db_session: AsyncSession) -> None:
    import uuid

    orch = make_orchestrator(db_session)
    result = await orch.run_capability(
        capability="profile_summary",
        profile_id=str(uuid.uuid4()),
        user_input="x",
    )

    assert result["status"] == "FAILED"
    assert result["error"] is not None
