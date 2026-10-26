"""LLM provider abstraction.

The rest of the application must NOT import a vendor SDK directly. All LLM
interaction goes through the :class:`LLMProvider` protocol defined here, which
keeps provider-specific secrets server-side and makes swapping providers
straightforward.
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

T = TypeVar("T", bound=BaseModel)


class LLMUsage(BaseModel):
    """Usage metadata for an LLM call."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class LLMResponse(BaseModel):
    """Structured response from an LLM provider.

    Provider-specific response objects are never exposed outside the provider
    implementation. Everything here is application-level.
    """

    model_config = ConfigDict(frozen=True)

    content: str
    """Primary generated text content."""

    structured_output: dict[str, Any] | None = None
    """Parsed/validated structured output when ``response_schema`` was provided
    and the provider supports native structured output (or was validated at the
    application level)."""

    provider: str
    """Provider identifier (e.g. ``"fake"``, ``"openai"``)."""

    model: str
    """Model identifier used for the call."""

    usage: LLMUsage
    """Token usage metadata."""

    request_id: str
    """Unique identifier for this LLM request."""

    metadata: dict[str, Any] = {}
    """Additional provider-neutral request/response metadata."""


class LLMProvider(Protocol):
    """Vendor-independent LLM provider interface.

    Applications depend on this abstraction, never on a vendor SDK directly.
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        """Generate a completion.

        Args:
            messages: Chat-style messages (role/content).
            tools: Optional tool definitions the model may call.
            response_schema: Optional Pydantic model to validate/parse the
                output into. If the provider supports native structured output,
                it is used there; otherwise the result is validated at the
                application level.
        """
        ...

    async def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_schema: type[T],
        *,
        tools: list[dict[str, Any]] | None = None,
    ) -> T:
        """Generate and return a parsed Pydantic model instance.

        The default implementation calls :meth:`generate` with
        ``response_schema`` and validates the returned ``structured_output``.
        Providers with native structured output may override this for better
        fidelity.
        """
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


def new_request_id() -> str:
    """Return a unique request identifier."""
    return uuid4().hex


# Fake provider (tests / local development). Imported last to avoid any
# circular import, since fake.py imports names defined above in this package.
from app.core.llm.fake import FakeLLMProvider  # noqa: E402

__all__ = [
    "FakeLLMProvider",
    "LLMProvider",
    "LLMResponse",
    "LLMUsage",
    "new_request_id",
]
