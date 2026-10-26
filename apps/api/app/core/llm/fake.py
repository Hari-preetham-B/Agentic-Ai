"""Deterministic fake LLM provider for tests and local development.

This provider requires no API key and produces deterministic responses suitable
for testing agent execution. It is clearly temporary infrastructure; real
providers (OpenAI, Groq, Gemini, ...) implement the same
:class:`~app.core.llm.LLMProvider` protocol and are swapped in via
configuration.

The fake provider inspects the request and returns a canned but plausible
structured output. It never calls an external API.
"""

from __future__ import annotations

from typing import Any, cast, List

from pydantic import BaseModel

from app.core.llm import LLMProvider, LLMResponse, LLMUsage, new_request_id


class FakeLLMProvider(LLMProvider):
    """Deterministic fake LLM provider.

    Used for tests and local development only. No credentials required.
    """

    provider_name = "fake"

    def __init__(self, model: str = "fake-model") -> None:
        self.model = model

    async def generate(
        self,
        messages: list[dict[str, str]],
        *,
        tools: list[dict[str, Any]] | None = None,
        response_schema: type[BaseModel] | None = None,
    ) -> LLMResponse:
        request_id = new_request_id()
        user_text = ""
        for message in reversed(messages):
            if message.get("role") == "user":
                user_text = message.get("content", "")
                break

        # Build deterministic structured output when a schema is requested.
        structured_output: dict[str, Any] | None = None
        if response_schema is not None:
            structured_output = self._build_structured(
                response_schema, user_text, tools
            )

        content = self._default_content(user_text, tools)

        return LLMResponse(
            content=content,
            structured_output=structured_output,
            provider=self.provider_name,
            model=self.model,
            usage=LLMUsage(
                input_tokens=len(user_text.split()),
                output_tokens=len(content.split()),
                total_tokens=len(user_text.split()) + len(content.split()),
            ),
            request_id=request_id,
            metadata={"deterministic": True},
        )

    def _default_content(
        self, user_text: str, tools: list[dict[str, Any]] | None
    ) -> str:
        if tools:
            tool_names = ", ".join(t.get("name", "unknown") for t in tools)
            return (
                f"FakeLLMProvider deterministic response. "
                f"Received input: {user_text[:80]}... "
                f"Available tools: {tool_names}."
            )
        return (
            f"FakeLLMProvider deterministic response. "
            f"Received input: {user_text[:80]}..."
        )

    def _build_structured(
        self,
        response_schema: type[BaseModel],
        user_text: str,
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        """Build a deterministic instance of the given Pydantic schema.

        This inspects schema fields and fills them with deterministic placeholder
        values derived from the input text. It does NOT fabricate information;
        for the profile summary workflow the caller (Profile Agent) is
        responsible for populating fields from actual retrieved profile data.
        """
        data: dict[str, Any] = {}
        for field_name, field_info in response_schema.model_fields.items():
            annotation = field_info.annotation
            data[field_name] = self._fill_field(field_name, annotation, user_text)
        try:
            instance = response_schema.model_validate(data)
            return cast(dict[str, Any], instance.model_dump())
        except Exception:
            # If validation fails, return the raw best-effort data so the
            # application-level validation can surface a clear error.
            return data

    def _fill_field(
        self, field_name: str, annotation: Any, user_text: str
    ) -> Any:
        origin = getattr(annotation, "__origin__", None)
        args = getattr(annotation, "__args__", None)

        # Optional[X] -> X
        if origin is None and str(annotation).startswith("typing.Optional"):
            annotation = args[0] if args else str
            origin = getattr(annotation, "__origin__", None)
            args = getattr(annotation, "__args__", None)

        if origin is list or origin is List:
            item_type = args[0] if args else str
            return [self._fill_field(f"{field_name}[0]", item_type, user_text)]
        if origin is dict:
            return {}
        if annotation is str:
            return f"Deterministic value for {field_name} (input: {user_text[:40]}...)"
        if annotation is int:
            return 0
        if annotation is float:
            return 0.0
        if annotation is bool:
            return False
        # Unknown/complex types: return None so Pydantic can apply defaults.
        return None


# Module-level default instance used by tests and the API layer. Swappable for
# real providers later.
fake_llm_provider = FakeLLMProvider()
