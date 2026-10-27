"""Tests for the Profile Agent and agent stubs."""

from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, set_engine_for_testing
from app.models.profile import Profile
from app.services.repositories import ProfileRepository
from app.agents import ProfileAgent
from app.agents.contracts import AgentState, AgentStatus
from app.core.llm import FakeLLMProvider
from app.tools import tool_registry
from app.tools.profile_tool import build_get_profile_tool


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
        repo = ProfileRepository(session)
        profile = Profile(
            full_name="Ada Lovelace",
            headline="Aspiring engineer",
            email="ada@example.com",
            profile_status="DRAFT",
        )
        session.add(profile)
        await session.flush()
        await session.refresh(profile)
        session.profile_id = profile.id  # type: ignore[attr-defined]
        # add a skill
        from app.models.profile import Skill

        session.add(
            Skill(
                profile_id=profile.id,
                name="Python",
                category="Programming",
                proficiency="ADVANCED",
                source="USER_CONFIRMED",
            )
        )
        await session.flush()
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_profile_agent_executes_and_produces_typed_result(
    db_session: AsyncSession,
) -> None:
    profile_id = db_session.profile_id  # type: ignore[attr-defined]
    tool = build_get_profile_tool(db_session)
    tool_registry.register(tool)

    agent = ProfileAgent(llm_provider=FakeLLMProvider())
    state = AgentState(
        profile_id=str(profile_id),
        user_input="Summarize my profile.",
        status=AgentStatus.RUNNING,
    )

    # First run: requests the get_profile tool.
    result1 = await agent.run(state)
    assert result1.status == AgentStatus.RUNNING
    assert state.context.get("tool_requested") == "get_profile"

    # Execute the tool and feed result back into state (simulating LangGraph).
    tool_result = await tool.execute(
        __import__("app.tools.profile_tool", fromlist=["GetProfileInput"]).GetProfileInput(  # noqa: E501
            profile_id=str(profile_id)
        )
    )
    assert tool_result.success is True
    state.tool_results["get_profile"] = tool_result.output
    state.context.pop("tool_requested", None)

    # Second run: produces the typed summary from real data.
    result2 = await agent.run(state)
    assert result2.status == AgentStatus.COMPLETED
    assert result2.output is not None
    assert result2.output["profile_id"] == str(profile_id)
    assert isinstance(result2.output["overview"], str)
    assert isinstance(result2.output["notable_skills"], list)
    assert "Python" in result2.output["notable_skills"]
    assert result2.duration_ms is not None
    assert result2.metadata["provider"] == "fake"


@pytest.mark.asyncio
async def test_agent_stubs_complete_without_fabrication() -> None:
    from app.agents import EvidenceAgent, InterviewAgent, LearningAgent

    for agent_cls in (LearningAgent, InterviewAgent, EvidenceAgent):
        agent = agent_cls()
        state = AgentState(
            profile_id="00000000-0000-0000-0000-000000000000",
            user_input="x",
            status=AgentStatus.RUNNING,
        )
        result = await agent.run(state)
        assert result.status == AgentStatus.COMPLETED
        assert result.output is not None
        assert result.output["status"] == "not_implemented"
        assert result.agent_name == agent.name


@pytest.mark.asyncio
async def test_profile_agent_missing_profile_id() -> None:
    agent = ProfileAgent(llm_provider=FakeLLMProvider())
    state = AgentState(
        profile_id=None,
        user_input="x",
        status=AgentStatus.RUNNING,
    )
    result = await agent.run(state)
    assert result.status == AgentStatus.FAILED
    assert len(result.errors) == 1
