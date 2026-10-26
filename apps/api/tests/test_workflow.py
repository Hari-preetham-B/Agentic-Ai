"""Tests for the LangGraph agent workflow."""

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, set_engine_for_testing
from app.models.profile import Profile
from app.services.repositories import ProfileRepository
from app.agents.contracts import AgentStatus
from app.tools import tool_registry
from app.tools.profile_tool import build_get_profile_tool
from app.workflows.agent_workflow import AgentWorkflow


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


@pytest.mark.asyncio
async def test_workflow_starts_and_completes_profile_summary(
    db_session: AsyncSession,
) -> None:
    profile_id = str(db_session.profile_id)  # type: ignore[attr-defined]
    tool = build_get_profile_tool(db_session)
    tool_registry.register(tool)

    workflow = AgentWorkflow()
    final_state = await workflow.run(
        current_agent="profile_agent",
        profile_id=profile_id,
        request_id="req-1",
        user_input="Summarize my profile.",
    )

    assert final_state.status == AgentStatus.COMPLETED
    assert final_state.agent_outputs is not None
    output = final_state.agent_outputs.get("profile_agent")
    assert output is not None
    assert output["profile_id"] == profile_id
    assert isinstance(output["overview"], str)
    assert isinstance(output["notable_skills"], list)


@pytest.mark.asyncio
async def test_workflow_tool_branch_executes_get_profile(
    db_session: AsyncSession,
) -> None:
    profile_id = str(db_session.profile_id)  # type: ignore[attr-defined]
    tool = build_get_profile_tool(db_session)
    tool_registry.register(tool)

    workflow = AgentWorkflow()
    final_state = await workflow.run(
        current_agent="profile_agent",
        profile_id=profile_id,
        request_id="req-2",
        user_input="Summary please.",
    )

    # The tool should have been executed and its result stored.
    assert "get_profile" in final_state.tool_results
    tool_result = final_state.tool_results["get_profile"]
    assert tool_result is not None
    assert tool_result.get("full_name") == "Ada Lovelace"


@pytest.mark.asyncio
async def test_workflow_unknown_agent_fails() -> None:
    workflow = AgentWorkflow()
    final_state = await workflow.run(
        current_agent="nonexistent_agent",
        profile_id=None,
        request_id="req-3",
        user_input="x",
    )

    assert final_state.status == AgentStatus.FAILED
    assert len(final_state.errors) >= 1
    assert "Unknown agent" in final_state.errors[0]["message"]
