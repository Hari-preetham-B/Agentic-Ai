"""Tests for the execution trace service."""

import uuid
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, set_engine_for_testing
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
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_start_run_creates_run_and_run_started_event(
    db_session: AsyncSession,
) -> None:
    trace = TraceService(db_session)
    run = await trace.start_run(
        request_id="req-1",
        capability="profile_summary",
        profile_id=uuid.uuid4(),
        provider="fake",
        model="fake-model",
    )

    assert run.id is not None
    assert run.capability == "profile_summary"
    # start_run leaves the run PENDING; completion happens via complete_run.
    assert run.status == "PENDING"

    events = await trace.event_repo.list_for_run(run.id)
    assert len(events) == 1
    assert events[0].event_type == "RUN_STARTED"
    assert events[0].sequence == 1
    assert events[0].payload is not None
    assert events[0].payload["capability"] == "profile_summary"


@pytest.mark.asyncio
async def test_emit_orders_events_by_sequence(db_session: AsyncSession) -> None:
    trace = TraceService(db_session)
    run = await trace.start_run(
        request_id="req-2",
        capability="skill_gap",
    )

    await trace.emit(
        run_id=run.id,
        event_type="AGENT_STARTED",
        agent_name="profile_agent",
        message="agent started",
    )
    await trace.emit(
        run_id=run.id,
        event_type="TOOL_STARTED",
        tool_name="get_profile",
        message="tool started",
    )
    await trace.emit(
        run_id=run.id,
        event_type="TOOL_COMPLETED",
        tool_name="get_profile",
        message="tool done",
    )

    events = await trace.event_repo.list_for_run(run.id)
    sequences = [e.sequence for e in events]
    assert sequences == sorted(sequences)
    assert sequences == [1, 2, 3, 4]
    event_types = [e.event_type for e in events]
    assert event_types == ["RUN_STARTED", "AGENT_STARTED", "TOOL_STARTED", "TOOL_COMPLETED"]


@pytest.mark.asyncio
async def test_complete_and_fail_run(db_session: AsyncSession) -> None:
    trace = TraceService(db_session)
    run = await trace.start_run(
        request_id="req-3",
        capability="profile_summary",
    )

    await trace.complete_run(run, message="done")
    assert run.status == "COMPLETED"
    assert run.completed_at is not None

    events = await trace.event_repo.list_for_run(run.id)
    types = [e.event_type for e in events]
    assert "RUN_COMPLETED" in types


@pytest.mark.asyncio
async def test_fail_run_records_error(db_session: AsyncSession) -> None:
    trace = TraceService(db_session)
    run = await trace.start_run(
        request_id="req-4",
        capability="evidence_check",
    )

    await trace.fail_run(run, error="boom", message="failed")
    assert run.status == "FAILED"
    assert run.error == "boom"
    assert run.completed_at is not None

    events = await trace.event_repo.list_for_run(run.id)
    types = [e.event_type for e in events]
    assert "RUN_FAILED" in types
    failed_event = [e for e in events if e.event_type == "RUN_FAILED"][0]
    assert failed_event.payload is not None
    assert failed_event.payload["error"] == "boom"


@pytest.mark.asyncio
async def test_no_chain_of_thought_in_payload(db_session: AsyncSession) -> None:
    trace = TraceService(db_session)
    run = await trace.start_run(
        request_id="req-5",
        capability="profile_summary",
    )
    await trace.emit(
        run_id=run.id,
        event_type="AGENT_THINKING",
        agent_name="profile_agent",
        message="evaluating profile",
        payload={"step": 1},
    )
    events = await trace.event_repo.list_for_run(run.id)
    thinking = [e for e in events if e.event_type == "AGENT_THINKING"][0]
    # payload contains only sanitized metadata, no hidden reasoning text.
    assert "reasoning" not in str(thinking.payload).lower()
    assert "chain" not in str(thinking.payload).lower()
    assert thinking.payload == {"step": 1}
