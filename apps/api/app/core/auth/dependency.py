"""FastAPI authentication dependency.

Extracts the Bearer token from the Authorization header and validates it
using the configured AuthProvider. Returns an AuthenticatedUser.

Usage in routes:
    from app.core.auth.dependency import get_current_user

    @router.get("/protected")
    async def protected(user: AuthenticatedUser = Depends(get_current_user)):
        ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth.provider import (
    AuthenticatedUser,
    FakeAuthProvider,
    AuthProvider,
)
from app.core.config import get_settings
from app.core.database import get_session

_security = HTTPBearer(auto_error=False)

# Default provider — swappable for real Supabase provider.
_auth_provider: AuthProvider | None = None


def get_auth_provider() -> AuthProvider:
    """Return the configured auth provider."""
    global _auth_provider
    if _auth_provider is None:
        settings = get_settings()
        # Use real Supabase provider if configured, else fake.
        if getattr(settings, "supabase_url", None):
            from app.core.auth.supabase_provider import SupabaseAuthProvider

            _auth_provider = SupabaseAuthProvider(
                supabase_url=settings.supabase_url,
            )
        else:
            _auth_provider = FakeAuthProvider()
    return _auth_provider


def set_auth_provider(provider: AuthProvider) -> None:
    """Override the auth provider (for testing)."""
    global _auth_provider
    _auth_provider = provider


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security),
) -> AuthenticatedUser:
    """FastAPI dependency that validates the Bearer token.

    Raises 401 if no credentials or invalid token.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    provider = get_auth_provider()
    try:
        user = await provider.validate_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


__all__ = [
    "get_current_user",
    "get_auth_provider",
    "set_auth_provider",
    "AuthenticatedUser",
]
