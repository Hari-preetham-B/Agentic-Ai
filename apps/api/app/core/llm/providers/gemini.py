"""Gemini LLM provider using the official google-genai SDK.

Implements the LLMProvider protocol. Uses Gemini's native structured output
for schema-constrained generation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.core.llm import LLMProvider, LLMResponse, LLMUsage, new_request_id

logger = logging.getLogger(__name__)

# Transient error indicators for retry logic.
_TRANSIENT_INDICATORS = [
    "rate limit",
    "429",
    "503",
    "502",
    "timeout",
    "temporarily unavailable",
    "resource exhausted",
]

_MAX_RETRIES = 3
_RETRY_DELAY = 1.0


class GeminiLLMProvider:
    """LLM provider using Google's Gemini API via the google-genai SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.8-flash",
        timeout: float = 60.0,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini API key is required but not provided.")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout
        self._client = genai.Client(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model(self) -> str:
        return self._model

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Generate a completion using Gemini."""
        request_id = new_request_id()

        # Convert messages to Gemini format.
        contents = self._convert_messages(messages)

        # Build config.
        config_kwargs: dict[str, Any] = {}
        if response_schema is not None:
            config_kwargs["response_mime_type"] = "application/json"
            config_kwargs["response_schema"] = response_schema

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        # Call Gemini with retry for transient errors.
        response = await self._call_with_retry(
            lambda: self._client.models.generate_content(
                model=self._model,
                contents=contents,
                config=config,
            )
        )

        # Extract content.
        content = response.text or ""

        # Parse structured output if schema was provided.
        structured_output = None
        if response_schema is not None and response.parsed is not None:
            try:
                parsed = response.parsed
                if hasattr(parsed, "model_dump"):
                    structured_output = parsed.model_dump()
                elif isinstance(parsed, dict):
                    structured_output = parsed
                else:
                    # Try to parse from text.
                    import json

                    structured_output = json.loads(content)
            except Exception:
                # Fall back to parsing text as JSON.
                try:
                    import json

                    structured_output = json.loads(content)
                except Exception:
                    structured_output = None

        # Extract usage.
        usage = LLMUsage()
        if response.usage_metadata:
            usage = LLMUsage(
                input_tokens=getattr(response.usage_metadata, "prompt_token_count", None),
                output_tokens=getattr(response.usage_metadata, "candidates_token_count", None),
                total_tokens=getattr(response.usage_metadata, "total_token_count", None),
            )

        return LLMResponse(
            content=content,
            structured_output=structured_output,
            provider=self.provider_name,
            model=self._model,
            usage=usage,
            request_id=request_id,
            metadata={"deterministic": False},
        )

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_schema: type[BaseModel],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> BaseModel:
        """Generate and return a parsed Pydantic model instance."""
        response = await self.generate(
            messages,
            tools=tools,
            response_schema=response_schema,
        )
        if response.structured_output is None:
            raise ValueError(
                f"Provider {self.provider_name} did not return structured output"
            )
        return response_schema.model_validate(response.structured_output)

    def _convert_messages(self, messages: list[dict[str, str]]) -> str:
        """Convert chat messages to a single prompt string for Gemini."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
            else:
                parts.append(content)
        return "\n\n".join(parts)

    async def _call_with_retry(self, func):
        """Call a function with retry for transient errors."""
        last_exception = None
        for attempt in range(_MAX_RETRIES):
            try:
                # Run in executor since the SDK is synchronous.
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(None, func)
            except Exception as exc:
                last_exception = exc
                error_msg = str(exc).lower()
                is_transient = any(
                    indicator in error_msg for indicator in _TRANSIENT_INDICATORS
                )
                if not is_transient or attempt == _MAX_RETRIES - 1:
                    raise
                await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
        raise last_exception  # type: ignore[misc]


__all__ = ["GeminiLLMProvider"]
