"""Tests for the agent runs API endpoints."""

import anyio
import pytest
from httpx import AsyncClient

from app.main import app


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.mark.anyio
async def test_agent_runs_endpoints(client: AsyncClient) -> None:
    # POST /agent-runs with a stub capability (no profile needed)
    resp = await client.post(
        "/agent-runs",
        json={
            "profile_id": "00000000-0000-0000-0000-000000000001",
            "capability": "career_analysis",
            "input": "Analyze my career options.",
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
    resp = await client.get(f"/agent-runs/{run_id}")
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["id"] == run_id
    assert detail["capability"] == "career_analysis"
    assert detail["status"] == "COMPLETED"
    assert len(detail["events"]) >= 1
    assert any(e["event_type"] == "RUN_STARTED" for e in detail["events"])

    # GET /agent-runs/{run_id}/events
    resp = await client.get(f"/agent-runs/{run_id}/events")
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
async def test_profile_summary_without_profile_fails(client: AsyncClient) -> None:
    resp = await client.post(
        "/agent-runs",
        json={
            "profile_id": "00000000-0000-0000-0000-000000000001",
            "capability": "profile_summary",
            "input": "Summarize my current profile.",
        },
    )
    assert resp.status_code == 202, resp.text
    body = resp.json()
    assert body["status"] == "FAILED"
    assert body["error"] is not None


@pytest.mark.anyio
async def test_agent_runs_unsupported_capability(client: AsyncClient) -> None:
    resp = await client.post(
        "/agent-runs",
        json={
            "profile_id": "00000000-0000-0000-0000-000000000001",
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
    resp = await client.get("/agent-runs/00000000-0000-0000-0000-000000000999")
    assert resp.status_code == 404

    resp = await client.get(
        "/agent-runs/00000000-0000-0000-0000-000000000999/events"
    )
    assert resp.status_code == 404
