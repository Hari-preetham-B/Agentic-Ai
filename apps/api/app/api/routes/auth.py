"""Authentication routes.

Provides a protected /auth/me endpoint that returns the authenticated
user's identity after validating the Bearer token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth.dependency import get_current_user
from app.core.auth.provider import AuthenticatedUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=dict)
async def get_current_user_profile(
    user: AuthenticatedUser = Depends(get_current_user),
) -> dict:
    """Return the authenticated user's identity.

    Requires a valid Bearer token in the Authorization header.
    """
    return {
        "user_id": user.user_id,
        "email": user.email,
        "provider": user.metadata.get("provider", "unknown"),
    }


__all__ = ["router"]
