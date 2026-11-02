"""Authentication provider abstraction.

The rest of the application must NOT import a vendor SDK directly. All
authentication interaction goes through the :class:`AuthProvider` protocol
defined here, which keeps provider-specific secrets server-side and makes
swapping providers straightforward.

A :class:`FakeAuthProvider` is provided for tests and local development.
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class AuthenticatedUser(BaseModel):
    """Authenticated user identity.

    Represents an authenticated user regardless of the underlying provider.
    Contains only non-sensitive identifying information.
    """

    model_config = ConfigDict(frozen=True)

    user_id: str
    email: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuthProvider(Protocol):
    """Vendor-independent authentication provider interface.

    Applications depend on this abstraction, never on a vendor SDK directly.
    """

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate a bearer token and return the authenticated user.

        Args:
            token: Bearer token string (without the ``Bearer `` prefix).

        Raises:
            ValueError: If the token is invalid, expired, or otherwise
                unacceptable.
        """
        ...


class FakeAuthProvider:
    """Deterministic fake auth provider for tests and local development.

    Accepts tokens of the form ``fake:<user_id>:<email>`` and returns the
    corresponding authenticated user. Rejects all other tokens.
    """

    provider_name = "fake"

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate a fake bearer token.

        Accepts tokens of the form ``fake:<user_id>:<email>``. Rejects all
        other tokens.
        """
        if not token or not token.startswith("fake:"):
            raise ValueError("Invalid authentication token.")

        parts = token.split(":", 2)
        if len(parts) < 2:
            raise ValueError("Malformed authentication token.")

        user_id = parts[1]
        email = parts[2] if len(parts) > 2 else None

        if not user_id:
            raise ValueError("Invalid user ID in token.")

        return AuthenticatedUser(
            user_id=user_id,
            email=email,
            metadata={"provider": "fake"},
        )


__all__ = [
    "AuthProvider",
    "AuthenticatedUser",
    "FakeAuthProvider",
]
