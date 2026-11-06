"""Authentication routes.

Provides:
- ``GET /auth/me``     — the authenticated user's identity.
- ``POST /auth/signup`` — account creation that works with either Supabase
  email confirmation setting. The account is created with the Supabase admin
  API (server-side secret key) so the user can sign in immediately instead of
  being blocked on a confirmation email.
"""

from __future__ import annotations

import re
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.auth.dependency import get_current_user
from app.core.auth.provider import AuthenticatedUser
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=320)
    password: str = Field(..., min_length=8, max_length=200)


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


@router.post("/signup", response_model=dict, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest) -> dict[str, Any]:
    """Create an account.

    Uses the Supabase admin API so the account is usable immediately, even
    when the project has "Confirm email" enabled (the default). The secret
    key stays server-side; the browser never sees it.
    """
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sign-up requires SUPABASE_URL and SUPABASE_SECRET_KEY.",
        )

    email = payload.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Enter a valid email address.",
        )

    base_url = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_secret_key,
        "Authorization": f"Bearer {settings.supabase_secret_key}",
        "Content-Type": "application/json",
    }
    body = {
        "email": email,
        "password": payload.password,
        "email_confirm": settings.auto_confirm_signups,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                f"{base_url}/auth/v1/admin/users", headers=headers, json=body
            )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not reach Supabase: {exc}",
        ) from exc

    if response.status_code >= 400:
        message = ""
        try:
            data = response.json()
            message = data.get("msg") or data.get("error_description") or data.get("message") or ""
        except Exception:  # noqa: BLE001 - fall back to raw text
            message = response.text
        if "already" in message.lower() or "exists" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists. Sign in instead.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message or "Could not create the account.",
        )

    data = response.json()
    return {
        "user_id": data.get("id"),
        "email": data.get("email", email),
        "email_confirmed": bool(data.get("email_confirmed_at")),
    }


__all__ = ["router"]
