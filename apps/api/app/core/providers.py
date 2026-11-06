"""Provider factory functions.

Selects the appropriate LLM or embedding provider based on configuration.
"""

from __future__ import annotations

from app.core.config import get_settings_no_cache as get_settings
from app.core.embedding import FakeEmbeddingProvider, EmbeddingProvider
from app.core.llm import FakeLLMProvider, LLMProvider


def create_llm_provider() -> LLMProvider:
    """Create an LLM provider based on configuration."""
    settings = get_settings()
    provider_name = (settings.llm_provider or "fake").lower()

    if provider_name == "gemini":
        from app.core.llm.providers.gemini import GeminiLLMProvider

        api_key = settings.llm_api_key
        if not api_key:
            raise ValueError("LLM_API_KEY is required for Gemini provider.")
        fallbacks = [
            m.strip()
            for m in (settings.llm_fallback_models or "").split(",")
            if m.strip()
        ]
        return GeminiLLMProvider(
            api_key=api_key,
            model=settings.llm_model or "gemini-3.8-flash",
            fallback_models=fallbacks,
        )

    # Default: fake provider for development and testing.
    return FakeLLMProvider()


def create_embedding_provider() -> EmbeddingProvider:
    """Create an embedding provider based on configuration."""
    settings = get_settings()
    provider_name = (settings.embedding_provider or "fake").lower()

    if provider_name == "gemini":
        from app.core.embedding.providers.gemini import GeminiEmbeddingProvider

        api_key = settings.embedding_api_key
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY is required for Gemini provider.")
        return GeminiEmbeddingProvider(
            api_key=api_key,
            model=settings.embedding_model or "gemini-embedding-2",
            dimension=settings.embedding_dimension,
        )

    # Default: fake provider for development and testing.
    return FakeEmbeddingProvider()


__all__ = ["create_llm_provider", "create_embedding_provider"]
