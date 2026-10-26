"""Tests for the LLM provider abstraction and FakeLLMProvider."""

import pytest

from app.core.llm import FakeLLMProvider, LLMResponse, LLMUsage, new_request_id


def test_new_request_id_is_unique() -> None:
    a = new_request_id()
    b = new_request_id()
    assert a != b
    assert len(a) > 0


@pytest.mark.asyncio
async def test_fake_provider_requires_no_key() -> None:
    provider = FakeLLMProvider(model="test-model")
    assert provider.provider_name == "fake"
    assert provider.model == "test-model"


@pytest.mark.asyncio
async def test_fake_provider_generate_returns_response() -> None:
    provider = FakeLLMProvider()
    response = await provider.generate(
        [{"role": "user", "content": "Summarize my profile."}]
    )
    assert isinstance(response, LLMResponse)
    assert response.provider == "fake"
    assert response.model == "fake-model"
    assert response.request_id
    assert isinstance(response.usage, LLMUsage)
    assert isinstance(response.content, str)
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_fake_provider_deterministic() -> None:
    messages = [{"role": "user", "content": "Hello"}]
    r1 = await FakeLLMProvider().generate(messages)
    r2 = await FakeLLMProvider().generate(messages)
    # Content deterministic given same input; request_id differs.
    assert r1.content == r2.content
    assert r1.request_id != r2.request_id


@pytest.mark.asyncio
async def test_fake_provider_structured_output() -> None:
    from pydantic import BaseModel, Field

    class Summary(BaseModel):
        overview: str = Field(...)
        strengths: list[str] = Field(default_factory=list)

    provider = FakeLLMProvider()
    result = await provider.generate_structured(
        [{"role": "user", "content": "Summarize."}],
        response_schema=Summary,
    )
    assert isinstance(result, Summary)
    assert isinstance(result.overview, str)
    assert isinstance(result.strengths, list)


@pytest.mark.asyncio
async def test_fake_provider_usage_metadata() -> None:
    provider = FakeLLMProvider()
    response = await provider.generate(
        [{"role": "user", "content": "a b c d e"}]
    )
    assert response.usage.input_tokens == 5
    assert response.usage.output_tokens is not None
    assert response.usage.output_tokens > 0


@pytest.mark.asyncio
async def test_fake_provider_with_tools() -> None:
    provider = FakeLLMProvider()
    tools = [{"name": "get_profile", "description": "Get profile"}]
    response = await provider.generate(
        [{"role": "user", "content": "x"}],
        tools=tools,
    )
    assert "get_profile" in response.content


def test_llm_usage_defaults() -> None:
    usage = LLMUsage()
    assert usage.input_tokens is None
    assert usage.total_tokens is None
