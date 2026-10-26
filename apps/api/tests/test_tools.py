"""Tests for the tool system: registry, lookup, and get_profile tool."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import set_engine_for_testing
from app.models.profile import Profile, Skill
from app.services.repositories import ProfileRepository
from app.tools import tool_registry
from app.tools.profile_tool import GetProfileInput, build_get_profile_tool


@pytest_asyncio.fixture
async def seeded_profile(session: AsyncSession) -> str:
    """Seed a profile with a skill and return its id."""
    repo = ProfileRepository(session)
    profile = Profile(
        full_name="Ada Lovelace",
        headline="Student",
        email="ada@example.com",
        profile_status="DRAFT",
    )
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
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
    return str(profile.id)


@pytest.mark.asyncio
async def test_tool_registration_and_lookup(seeded_profile: str) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    # Rebuild a tool bound to the current session via the orchestrator pattern.
    # We need a session; grab it from the seeded_profile fixture indirectly.
    # Simpler: register via a fresh tool using the same session is not possible
    # here, so instead verify registry behavior with an in-memory tool.
    from app.tools import Tool
    from pydantic import BaseModel

    class In(BaseModel):
        x: int

    class Out(BaseModel):
        y: int

    class DummyTool(Tool[In, Out]):
        input_schema = In
        output_schema = Out

        async def _run(self, input_data: In) -> dict[str, int]:
            return {"y": input_data.x + 1}

    tool = DummyTool(name="dummy", description="dummy")
    tool_registry.register(tool)
    assert tool_registry.has("dummy")
    assert tool_registry.get("dummy") is tool
    assert "dummy" in tool_registry.list()
    result = await tool.execute({"x": 1})
    assert result.success is True
    assert result.output == {"y": 2}


def test_unknown_tool_fails_safely() -> None:
    assert tool_registry.get("nonexistent_tool") is None
    assert "nonexistent_tool" not in tool_registry.list()


@pytest.mark.asyncio
async def test_get_profile_tool_retrieves_profile(
    session: AsyncSession, seeded_profile: str
) -> None:
    tool = build_get_profile_tool(session)
    result = await tool.execute(GetProfileInput(profile_id=seeded_profile))
    assert result.success is True
    assert result.output is not None
    assert result.output["id"] == seeded_profile
    assert result.output["full_name"] == "Ada Lovelace"
    assert result.output["profile_status"] == "DRAFT"
    assert result.duration_ms is not None
    assert any(s["name"] == "Python" for s in result.output["skills"])


@pytest.mark.asyncio
async def test_get_profile_tool_invalid_id(session: AsyncSession) -> None:
    tool = build_get_profile_tool(session)
    result = await tool.execute(GetProfileInput(profile_id="not-a-uuid"))
    assert result.success is False
    assert result.error is not None


@pytest.mark.asyncio
async def test_get_profile_tool_missing_profile(session: AsyncSession) -> None:
    import uuid

    tool = build_get_profile_tool(session)
    result = await tool.execute(GetProfileInput(profile_id=str(uuid.uuid4())))
    assert result.success is False
    assert "not found" in (result.error or "")


def test_tool_definition_shape() -> None:
    from app.tools.profile_tool import GetProfileInput, GetProfileOutput

    input_schema = GetProfileInput.model_json_schema()
    output_schema = GetProfileOutput.model_json_schema()
    assert input_schema["type"] == "object"
    assert "profile_id" in input_schema["properties"]
    assert output_schema["type"] == "object"
    assert "id" in output_schema["properties"]
