"""Tests for embedding provider."""

import asyncio

import pytest

from app.core.embedding import FakeEmbeddingProvider


@pytest.mark.asyncio
async def test_fake_embedding_deterministic() -> None:
    """Test that fake embedding provider produces deterministic outputs."""
    provider = FakeEmbeddingProvider()
    vec1 = await provider.embed_text("Python is a core skill")
    vec2 = await provider.embed_text("Python is a core skill")
    assert vec1 == vec2
    assert len(vec1) == 384
    assert all(-1.0 <= v <= 1.0 for v in vec1)


@pytest.mark.asyncio
async def test_fake_embedding_different_inputs() -> None:
    """Test that different inputs produce different embeddings."""
    provider = FakeEmbeddingProvider()
    vec1 = await provider.embed_text("Python")
    vec2 = await provider.embed_text("Java")
    assert vec1 != vec2


@pytest.mark.asyncio
async def test_fake_embedding_documents() -> None:
    """Test batch document embedding."""
    provider = FakeEmbeddingProvider()
    vecs = await provider.embed_documents(["Python", "Java", "SQL"])
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)
    assert vecs[0] != vecs[1] != vecs[2]


def test_fake_embedding_provider_properties() -> None:
    """Test provider metadata."""
    provider = FakeEmbeddingProvider()
    assert provider.provider_name == "fake"
    assert provider.model == "fake-embedding-model"
    assert provider.dimension == 384


__all__ = [
    "test_fake_embedding_deterministic",
    "test_fake_embedding_different_inputs",
    "test_fake_embedding_documents",
    "test_fake_embedding_provider_properties",
]
