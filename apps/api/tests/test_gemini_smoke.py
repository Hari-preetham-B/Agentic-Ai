"""Gemini provider smoke test.

Run manually with:
    cd apps/api
    python -m pytest tests/test_gemini_smoke.py -v -s

Requires LLM_PROVIDER=gemini and EMBEDDING_PROVIDER=gemini in .env
with valid API keys.
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

import pytest
from app.core.config import get_settings

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_GEMINI_SMOKE") != "1",
    reason="Smoke test requires RUN_GEMINI_SMOKE=1 and real Gemini API credentials.",
)
from app.core.llm import LLMResponse
from pydantic import BaseModel


class SmokeSchema(BaseModel):
    greeting: str
    number: int


@pytest.mark.asyncio
async def test_gemini_llm_smoke():
    """Smoke test: send a minimal prompt to Gemini."""
    settings = get_settings()
    assert settings.llm_provider == "gemini", "LLM_PROVIDER must be gemini"
    assert settings.llm_api_key, "LLM_API_KEY must be set"

    from app.core.providers import create_llm_provider

    provider = create_llm_provider()
    assert provider.provider_name == "gemini"

    # Text generation
    response = await provider.generate(
        [{"role": "user", "content": "Say hello in one sentence."}]
    )
    assert response.content
    assert response.provider == "gemini"
    assert response.model
    print(f"LLM smoke: OK (model={response.model}, tokens={response.usage.total_tokens})")

    # Structured output
    structured = await provider.generate_structured(
        [{"role": "user", "content": "Generate a greeting and a number."}],
        SmokeSchema,
    )
    assert isinstance(structured, SmokeSchema)
    assert structured.greeting
    assert isinstance(structured.number, int)
    print(f"Structured smoke: OK (greeting={structured.greeting}, number={structured.number})")


@pytest.mark.asyncio
async def test_gemini_embedding_smoke():
    """Smoke test: generate one embedding from Gemini."""
    settings = get_settings()
    assert settings.embedding_provider == "gemini", "EMBEDDING_PROVIDER must be gemini"
    assert settings.embedding_api_key, "EMBEDDING_API_KEY must be set"

    from app.core.providers import create_embedding_provider

    provider = create_embedding_provider()
    assert provider.provider_name == "gemini"
    assert provider.dimension == 384

    # Single embedding
    vec = await provider.embed_text("Hello world")
    assert len(vec) == 384
    print(f"Embedding smoke: OK (dimension={len(vec)})")

    # Batch embedding
    vecs = await provider.embed_documents(["Hello", "World"])
    assert len(vecs) == 2
    assert all(len(v) == 384 for v in vecs)
    print(f"Batch embedding smoke: OK ({len(vecs)} vectors, dim={len(vecs[0])})")


if __name__ == "__main__":
    asyncio.run(test_gemini_llm_smoke())
    asyncio.run(test_gemini_embedding_smoke())
    print("All smoke tests passed!")
