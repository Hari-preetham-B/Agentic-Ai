"""Gemini embedding provider using the official google-genai SDK.

Implements the EmbeddingProvider protocol. Uses gemini-embedding-2 with
384 output dimensions.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from google import genai
from google.genai import types

from app.core.embedding.provider import EmbeddingProvider, FakeEmbeddingProvider

logger = logging.getLogger(__name__)

_EXPECTED_DIMENSION = 384


class GeminiEmbeddingProvider:
    """Embedding provider using Google's Gemini API."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-embedding-2",
        dimension: int = 384,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required but not provided.")
        self._api_key = api_key
        self._model = model
        self._dimension = dimension
        self._client = genai.Client(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        vectors = await self.embed_documents([text])
        return vectors[0]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple text strings.

        Gemini's embed_content API returns one embedding per call,
        so we call it once per text.
        """
        if not texts:
            return []

        vectors = []
        for text in texts:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda t=text: self._client.models.embed_content(
                    model=self._model,
                    contents=t,
                    config=types.EmbedContentConfig(
                        output_dimensionality=self._dimension,
                        task_type="RETRIEVAL_DOCUMENT",
                    ),
                ),
            )

            if not response.embeddings:
                raise ValueError("No embeddings returned from Gemini.")

            vec = list(response.embeddings[0].values)
            if len(vec) != self._dimension:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self._dimension}, "
                    f"got {len(vec)}."
                )
            vectors.append(vec)

        return vectors


__all__ = ["GeminiEmbeddingProvider"]
