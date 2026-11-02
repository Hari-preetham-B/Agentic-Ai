"""Supabase authentication provider.

Validates Supabase JWT tokens using the project's JWKS endpoint.

Supabase authenticates users via JWT access tokens signed with the
project's private key. The corresponding public key is published via
the JWKS endpoint at ``/auth/v1/.well-known/jwks.json`` under the
Supabase project URL. This provider fetches and caches the JWKS,
then verifies incoming bearer tokens against the matching public key.

Provider name: ``supabase``

Activated when :data:`app.core.settings.SUPABASE_URL` is configured.
"""

from __future__ import annotations

import time
from typing import Any

import jwt
from jwt import PyJWKClient

from app.core.auth.provider import AuthenticatedUser, AuthProvider


class SupabaseAuthProvider:
    """Auth provider that validates Supabase JWT tokens using JWKS.

    Supabase authenticates users via JWT access tokens signed with the
    project's private key. The corresponding public key is published via
    the JWKS endpoint at ``/auth/v1/.well-known/jwks.json`` under the
    Supabase project URL. This provider fetches and caches the JWKS,
    then verifies incoming bearer tokens against the matching public key.

    Provider name: ``supabase``

    Activated when :data:`app.core.settings.SUPABASE_URL` is configured.
    """

    def __init__(
        self,
        supabase_url: str,
        supabase_secret_key: str | None = None,
        jwt_secret: str | None = None,
    ) -> None:
        self.supabase_url = supabase_url.rstrip("/")
        self._jwks_url = f"{self.supabase_url}/auth/v1/.well-known/jwks.json"
        self._jwks_client: PyJWKClient | None = None
        self._jwks_fetch_time: float | None = None
        # JWKS cache TTL: 5 minutes. Supabase rotates keys infrequently,
        # but a short TTL ensures we pick up rotation quickly.
        self._jwks_cache_ttl = 300.0

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate a Supabase JWT token.

        Uses the JWKS endpoint to verify the token signature and extract
        claims.

        Args:
            token: Bearer token string (without the ``Bearer `` prefix).

        Raises:
            ValueError: If the token is invalid, expired, or otherwise
                unacceptable.
        """
        if not token:
            raise ValueError("Missing authentication token.")

        # Get the JWKS client. If the endpoint is unreachable, fail closed
        # — never accept an unverified token.
        try:
            jwks_client = self._get_jwks_client()
        except Exception:
            raise ValueError("Unable to reach JWKS endpoint.")

        # Get the signing key for this token's key ID. If the key is
        # not found (e.g. key rotation), refresh the JWKS cache and try once
        # more.
        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
        except Exception:
            # Refresh the JWKS cache and retry once with a fresh client.
            self._jwks_client = None
            self._jwks_fetch_time = None
            jwks_client = self._get_jwks_client()
            try:
                signing_key = jwks_client.get_signing_key_from_jwt(token)
            except Exception as exc:
                raise ValueError(
                    "Invalid token: unable to find signing key."
                ) from exc

        try:
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience="authenticated",
                issuer=f"{self.supabase_url}/auth/v1",
                options={
                    "require": ["exp", "sub", "iss"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired.")
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}") from exc

        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token: missing subject.")

        email = payload.get("email")
        return AuthenticatedUser(
            user_id=user_id,
            email=email,
            metadata={"provider": "supabase"},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_jwks_client(self) -> PyJWKClient:
        """Return the JWKS client, refreshing the cache if expired."""
        now = time.time()
        if (
            self._jwks_client is not None
            and self._jwks_fetch_time is not None
            and now - self._jwks_fetch_time < self._jwks_cache_ttl
        ):
            return self._jwks_client

        self._jwks_client = PyJWKClient(self._jwks_url)
        self._jwks_fetch_time = now
        return self._jwks_client


__all__ = ["SupabaseAuthProvider"]
