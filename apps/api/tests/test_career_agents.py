"""Tests for Career Agent and Skill Gap Agent."""

import uuid
from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_engine_for_testing
from app.models.career import Career, CareerSkill
from app.models.profile import Profile, Skill
from app.services.career_knowledge_service import CareerKnowledgeService
from app.services.career_recommendation_service import CareerRecommendationService
from app.services.skill_matching import compute_skill_match
from app.agents.career_agents import CareerAgent, SkillGapAgent
from app.agents.contracts import AgentState, AgentStatus
from app.core.llm import FakeLLMProvider
from app.tools import tool_registry
from app.tools.career_tools import (
    build_get_career_tool,
    build_get_career_requirements_tool,
    build_calculate_skill_match_tool,
    GetCareerInput,
    CalculateSkillMatchInput,
)
from app.tools.profile_tool import build_get_profile_tool, GetProfileInput


@pytest_asyncio.fixture
async def seeded_data(session: AsyncSession) -> dict:
    """Seed a profile and career for agent testing."""
    profile_id = uuid.uuid4()
    career_id = uuid.uuid4()

    session.add(
        Profile(
            id=profile_id,
            full_name="Test User",
            headline="Software Engineer",
            email="test@example.com",
            profile_status="CONFIRMED",
        )
    )
    session.add(
        Skill(
            profile_id=profile_id,
            name="Python",
            category="Programming Language",
            proficiency="ADVANCED",
            source="USER_CONFIRMED",
        )
    )
    session.add(
        Skill(
            profile_id=profile_id,
            name="SQL",
            category="Database",
            proficiency="INTERMEDIATE",
            source="USER_CONFIRMED",
        )
    )

    career_slug = f"test-engineer-{uuid.uuid4().hex[:8]}"
    session.add(
        Career(
            id=career_id,
            slug=career_slug,
            title="Test Engineer",
            domain="Engineering",
            summary="A test career.",
            description="Test career description.",
        )
    )
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
    await session.commit()

    return {
        "profile_id": str(profile_id),
        "career_id": str(career_id),
        "career_slug": career_slug,
    }


@pytest.mark.asyncio
async def test_career_agent_full_flow(
    session: AsyncSession, seeded_data: dict
) -> None:
    """Test Career Agent full workflow through LangGraph."""
    # Register tools
    tool_registry.register(build_get_profile_tool(session))
    tool_registry.register(build_get_career_tool(session))
    tool_registry.register(build_get_career_requirements_tool(session))
    tool_registry.register(build_calculate_skill_match_tool(session))

    agent = CareerAgent(llm_provider=FakeLLMProvider())

    state = AgentState(
        profile_id=seeded_data["profile_id"],
        current_agent="career_agent",
        user_input="Analyze my fit for Test Engineer.",
        status=AgentStatus.RUNNING,
        context={"career_slug": seeded_data["career_slug"]},
    )

    # First invocation - requests get_profile tool
    result1 = await agent.run(state)
    assert result1.status == AgentStatus.RUNNING
    assert state.context.get("tool_requested") == "get_profile"

    # Execute get_profile tool
    profile_tool = build_get_profile_tool(session)
    profile_result = await profile_tool.execute(
        GetProfileInput(profile_id=seeded_data["profile_id"])
    )
    assert profile_result.success is True
    state.tool_results["get_profile"] = profile_result.output
    state.context.pop("tool_requested", None)

    # Second invocation - requests get_career tool
    result2 = await agent.run(state)
    assert result2.status == AgentStatus.RUNNING
    assert state.context.get("tool_requested") == "get_career"

    # Execute get_career tool
    career_tool = build_get_career_tool(session)
    career_result = await career_tool.execute(
        GetCareerInput(slug=seeded_data["career_slug"])
    )
    assert career_result.success is True
    state.tool_results["get_career"] = career_result.output
    state.context.pop("tool_requested", None)

    # Third invocation - requests calculate_skill_match tool
    result3 = await agent.run(state)
    assert result3.status == AgentStatus.RUNNING
    assert state.context.get("tool_requested") == "calculate_skill_match"

    # Execute calculate_skill_match tool
    match_tool = build_calculate_skill_match_tool(session)
    match_result = await match_tool.execute(
        CalculateSkillMatchInput(
            career_id=seeded_data["career_id"],
            career_title="Test Engineer",
            career_skills=career_result.output.get("skills", []),
            profile_skills=profile_result.output.get("skills", []),
        )
    )
    assert match_result.success is True
    state.tool_results["calculate_skill_match"] = match_result.output
    state.context.pop("tool_requested", None)

    # Fourth invocation - produces final result
    result4 = await agent.run(state)
    assert result4.status == AgentStatus.COMPLETED
    assert result4.output is not None
    assert result4.output["career_id"] == seeded_data["career_id"]
    assert result4.output["career_title"] == "Test Engineer"
    assert 0.0 <= result4.output["fit_score"] <= 1.0
    assert "fit_summary" in result4.output
    assert "strengths" in result4.output
    assert "skill_gaps" in result4.output
    assert result4.metadata["provider"] == "fake"


@pytest.mark.asyncio
async def test_skill_gap_agent_full_flow(
    session: AsyncSession, seeded_data: dict
) -> None:
    """Test Skill Gap Agent full workflow through LangGraph."""
    # Register tools
    tool_registry.register(build_get_profile_tool(session))
    tool_registry.register(build_get_career_tool(session))
    tool_registry.register(build_get_career_requirements_tool(session))
    tool_registry.register(build_calculate_skill_match_tool(session))

    agent = SkillGapAgent(llm_provider=FakeLLMProvider())

    state = AgentState(
        profile_id=seeded_data["profile_id"],
        current_agent="skill_gap_agent",
        user_input="What are my skill gaps for Test Engineer?",
        status=AgentStatus.RUNNING,
        context={"career_slug": seeded_data["career_slug"]},
    )

    # First invocation - requests get_profile tool
    result1 = await agent.run(state)
    assert result1.status == AgentStatus.RUNNING

    # Execute get_profile tool
    profile_tool = build_get_profile_tool(session)
    profile_result = await profile_tool.execute(
        GetProfileInput(profile_id=seeded_data["profile_id"])
    )
    assert profile_result.success is True
    state.tool_results["get_profile"] = profile_result.output
    state.context.pop("tool_requested", None)

    # Second invocation - requests get_career tool
    result2 = await agent.run(state)
    assert result2.status == AgentStatus.RUNNING

    # Execute get_career tool
    career_tool = build_get_career_tool(session)
    career_result = await career_tool.execute(
        GetCareerInput(slug=seeded_data["career_slug"])
    )
    assert career_result.success is True
    state.tool_results["get_career"] = career_result.output
    state.context.pop("tool_requested", None)

    # Third invocation - requests calculate_skill_match tool
    result3 = await agent.run(state)
    assert result3.status == AgentStatus.RUNNING

    # Execute calculate_skill_match tool
    match_tool = build_calculate_skill_match_tool(session)
    match_result = await match_tool.execute(
        CalculateSkillMatchInput(
            career_id=seeded_data["career_id"],
            career_title="Test Engineer",
            career_skills=career_result.output.get("skills", []),
            profile_skills=profile_result.output.get("skills", []),
        )
    )
    assert match_result.success is True
    state.tool_results["calculate_skill_match"] = match_result.output
    state.context.pop("tool_requested", None)

    # Fourth invocation - produces final result
    result4 = await agent.run(state)
    assert result4.status == AgentStatus.COMPLETED
    assert result4.output is not None
    assert result4.output["career_id"] == seeded_data["career_id"]
    assert result4.output["career_title"] == "Test Engineer"
    assert 0.0 <= result4.output["overall_score"] <= 1.0
    assert len(result4.output["priority_gaps"]) >= 0
    assert len(result4.output["matched_strengths"]) >= 0
    assert len(result4.output["recommendations"]) >= 0
    assert result4.metadata["provider"] == "fake"


@pytest.mark.asyncio
async def test_career_agent_missing_profile_id() -> None:
    """Test Career Agent with missing profile ID."""
    agent = CareerAgent(llm_provider=FakeLLMProvider())
    state = AgentState(
        profile_id=None,
        current_agent="career_agent",
        user_input="x",
        status=AgentStatus.RUNNING,
    )

    result = await agent.run(state)
    assert result.status == AgentStatus.FAILED
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_skill_gap_agent_missing_career_slug(
    session: AsyncSession,
) -> None:
    """Test Skill Gap Agent with missing career slug."""
    agent = SkillGapAgent(llm_provider=FakeLLMProvider())
    state = AgentState(
        profile_id="00000000-0000-0000-0000-000000000001",
        current_agent="skill_gap_agent",
        user_input="x",
        status=AgentStatus.RUNNING,
        context={},
    )

    result = await agent.run(state)
    assert result.status == AgentStatus.FAILED
    assert len(result.errors) == 1


__all__ = [
    "test_career_agent_full_flow",
    "test_skill_gap_agent_full_flow",
    "test_career_agent_missing_profile_id",
    "test_skill_gap_agent_missing_career_slug",
]
