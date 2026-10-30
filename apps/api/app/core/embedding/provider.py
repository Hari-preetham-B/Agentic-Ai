"""Embedding provider abstraction.

The rest of the application must NOT import a vendor SDK directly. All embedding
interaction goes through the :class:`EmbeddingProvider` protocol defined here,
which keeps provider-specific secrets server-side and makes swapping providers
straightforward.

A :class:`FakeEmbeddingProvider` is provided for tests and local development —
it requires no API key and produces deterministic embeddings.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar
from uuid import uuid4

T = TypeVar("T")


class EmbeddingResponse:
    """Structured response from an embedding provider."""

    def __init__(
        self,
        *,
        embeddings: list[list[float]],
        provider: str,
        model: str,
        usage: dict[str, int] | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.embeddings = embeddings
        self.provider = provider
        self.model = model
        self.usage = usage or {}
        self.request_id = request_id or uuid4().hex
        self.metadata = metadata or {}


class EmbeddingProvider(Protocol):
    """Vendor-independent embedding provider interface.

    Applications depend on this abstraction, never on a vendor SDK directly.
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""

    @property
    def model(self) -> str:
        """Model identifier used for embedding."""

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string and return its vector.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
        """
        ...

    async def embed_documents(
        self, texts: list[str]
    ) -> list[list[float]]:
        """Embed multiple text strings and return their vectors.

        Args:
            texts: The texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
        """
        ...


class FakeEmbeddingProvider:
    """Deterministic fake embedding provider for tests and local development.

    This provider requires no API key and produces deterministic embeddings
    derived from a hash of the input text. It never calls an external API.

    Embedding dimension is fixed at 384 for a small, predictable footprint.
    """

    provider_name = "fake"
    model = "fake-embedding-model"
    _dimension = 384

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        return self._embed_single(text)

    async def embed_documents(
        self, texts: list[str]
    ) -> list[list[float]]:
        return [self._embed_single(t) for t in texts]

    def _embed_single(self, text: str) -> list[float]:
        """Produce a deterministic pseudo-embedding from text.

        The vector is seeded by a hash of the text so identical inputs always
        produce identical outputs. Values are in [-1, 1].
        """
        import hashlib

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for i in range(self._dimension):
            byte = digest[i % len(digest)]
            # Map byte to [-1, 1]
            values.append((byte / 127.5) - 1.0)
        return values


__all__ = [
    "EmbeddingProvider",
    "EmbeddingResponse",
    "FakeEmbeddingProvider",
]
