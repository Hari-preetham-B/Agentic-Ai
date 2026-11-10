"""Regression tests for defects found while integrating CareerTwin end to end.

Each test pins a bug that previously reached users:
- roadmap retrieval crashed (NameError) so generated roadmaps could not load
- readiness crashed because a dependency-service method did not exist
- free-text agent input was used verbatim as a career slug
- a failed agent tool looped until LangGraph's recursion limit
- the tool registry was process-global, so concurrent requests shared tools
- the interview evaluation status violated the database CHECK constraint
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.scripts.seed_data import CAREERS, LEARNING_RESOURCES, SKILL_DEPENDENCIES
from app.scripts.seed_reference_data import (
    _upsert_career,
    _upsert_career_projects,
    _upsert_career_skills,
    _upsert_career_sources,
    _upsert_career_tools,
    _upsert_learning_resources,
    _upsert_skill_dependencies,
)
from app.schemas.profile import ProfileCreate
from app.services.learning_roadmap_service import LearningRoadmapService
from app.services.orchestrator import AgentOrchestrator, extract_career_slug
from app.services.profile_service import create_profile
from app.services.skill_dependency_service import SkillDependencyService
from app.tools import Tool, tool_registry


# -- career slug parsing ----------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("machine-learning-engineer", "machine-learning-engineer"),
        ("career_slug=data-analyst", "data-analyst"),
        ("Analyze my skill gaps for machine-learning-engineer.", "machine-learning-engineer"),
        ("  AI-Engineer  ", "ai-engineer"),
        ("", ""),
        (None, ""),
    ],
)
def test_extract_career_slug(raw, expected):
    assert extract_career_slug(raw) == expected


# -- dependency service -----------------------------------------------------


def test_get_missing_prerequisites_is_case_insensitive():
    service = SkillDependencyService(session=None)  # type: ignore[arg-type]
    graph = {"Deep Learning": ["Machine Learning", "Python"], "Python": []}
    assert service.get_missing_prerequisites("Deep Learning", graph, {"python"}) == ["Machine Learning"]
    assert service.get_missing_prerequisites("Python", graph, set()) == []
    assert service.get_missing_prerequisites("Unknown", graph, set()) == []


# -- tool registry isolation ------------------------------------------------


from pydantic import BaseModel


class _In(BaseModel):
    pass


class _Out(BaseModel):
    owner: str = ""


def _tool(owner: str) -> Tool:
    class _T(Tool[_In, _Out]):
        input_schema = _In
        output_schema = _Out

        async def _run(self, input_data: _In) -> dict:
            return {"owner": owner}

    return _T("shared_name", "test tool")


@pytest.mark.asyncio
async def test_tool_registry_is_isolated_per_task():
    """Two concurrent requests must never see each other's registered tools."""

    async def request(owner: str, other_done: asyncio.Event, me_done: asyncio.Event):
        tool_registry.register(_tool(owner))
        me_done.set()
        await other_done.wait()  # the other task has registered by now
        found = tool_registry.get("shared_name")
        result = await found.execute({})  # type: ignore[union-attr]
        return result.output["owner"]

    a_done, b_done = asyncio.Event(), asyncio.Event()
    a, b = await asyncio.gather(
        asyncio.create_task(request("A", b_done, a_done)),
        asyncio.create_task(request("B", a_done, b_done)),
    )
    assert (a, b) == ("A", "B")


# -- seeded fixtures --------------------------------------------------------


@pytest.fixture
async def seeded(session: AsyncSession):
    from app.models.career import Career, CareerProject, CareerSkill, CareerSource, CareerTool
    from app.models.learning import LearningResource, LearningResourceSkill, SkillDependency
    from app.models.profile import Profile

    for model in (CareerSkill, CareerTool, CareerProject, CareerSource, Career,
                  LearningResourceSkill, LearningResource, SkillDependency, Profile):
        await session.execute(delete(model))
    await session.commit()
    for data in CAREERS:
        cid = await _upsert_career(session, data)
        await _upsert_career_skills(session, cid, data.get("skills", []))
        await _upsert_career_tools(session, cid, data.get("tools", []))
        await _upsert_career_projects(session, cid, data.get("projects", []))
        await _upsert_career_sources(session, cid, data.get("sources", []))
    await _upsert_learning_resources(session, LEARNING_RESOURCES)
    await _upsert_skill_dependencies(session, SKILL_DEPENDENCIES)
    await session.commit()
    profile = await create_profile(
        session,
        ProfileCreate(full_name="Reg Test", headline="Student", email="r@example.com"),
        user_id=uuid.uuid4(),
    )
    await session.commit()
    return profile


@pytest.mark.asyncio
async def test_roadmap_can_be_generated_and_read_back_with_resources(session, seeded):
    service = LearningRoadmapService(session)
    created = await service.generate_roadmap(
        profile_id=str(seeded.id),
        career_slug="machine-learning-engineer",
        profile_skills=[{"name": "Python", "proficiency": "ADVANCED"}],
    )
    # Items must carry their persisted id (the UI keys rows and updates progress by it).
    assert all(item.get("id") for item in created["items"])
    loaded = await service.get_roadmap(created["roadmap_id"])  # used to raise NameError
    assert {i["id"] for i in loaded["items"]} == {i["id"] for i in created["items"]}
    assert loaded is not None
    assert loaded["items"], "roadmap should contain items"
    assert any(item["resources"] for item in loaded["items"]), "resources should load"
    # Prerequisites are sequenced before the skills that depend on them.
    order = {item["skill_name"]: item["sequence_order"] for item in loaded["items"]}
    if "Machine Learning" in order and "Deep Learning" in order:
        assert order["Machine Learning"] < order["Deep Learning"]


@pytest.mark.asyncio
async def test_failed_tool_ends_run_instead_of_hitting_recursion_limit(session, seeded):
    orchestrator = AgentOrchestrator(session=session)
    result = await orchestrator.run_capability(
        capability="skill_gap",
        profile_id=str(seeded.id),
        user_input="not-a-real-career",
    )
    assert result["status"] == "FAILED"
    assert "recursion" not in str(result.get("error", "")).lower()


@pytest.mark.asyncio
async def test_skill_gap_accepts_free_text_input(session, seeded):
    orchestrator = AgentOrchestrator(session=session)
    result = await orchestrator.run_capability(
        capability="skill_gap",
        profile_id=str(seeded.id),
        user_input="Analyze my skill gaps for machine-learning-engineer.",
    )
    assert result["status"] == "COMPLETED", result.get("error")
    assert result["result"]["career_title"] == "Machine Learning Engineer"


# -- interview evaluation status vs DB constraint --------------------------


def test_interview_evaluation_status_matches_check_constraint():
    import pathlib
    import re

    migration = pathlib.Path("alembic/versions/0005_adaptive_interview.py").read_text()
    constraint = re.search(r"evaluation_status IN \(([^)]*)\)", migration)
    assert constraint, "evaluation_status CHECK constraint not found"
    allowed = set(re.findall(r"'([A-Z_]+)'", constraint.group(1)))
    source = pathlib.Path("app/services/interview_flow_service.py").read_text()
    written = set(re.findall(r"evaluation_status\s*=\s*\"([A-Z_]+)\"", source))
    assert written, "expected evaluation_status assignments"
    assert written <= allowed, f"{written - allowed} not allowed by the database constraint"
