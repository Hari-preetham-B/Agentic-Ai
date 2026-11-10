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

import asyncio
import time
from typing import Any

import jwt
from jwt import PyJWKClient

from app.core.auth.provider import AuthenticatedUser, AuthProvider

# Asymmetric algorithms that a Supabase project may publish through JWKS.
_ALLOWED_ALGORITHMS = ("ES256", "ES384", "RS256", "RS384", "PS256")


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
        self._jwt_secret = jwt_secret or None
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

        try:
            header = jwt.get_unverified_header(token)
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}") from exc

        token_alg = header.get("alg")
        if token_alg == "HS256":
            # Legacy Supabase projects sign access tokens with a shared secret.
            # Verified only when SUPABASE_JWT_SECRET is configured; the key
            # type (secret vs. public key) is never taken from the token.
            if not self._jwt_secret:
                raise ValueError(
                    "Token uses the legacy HS256 signing key but "
                    "SUPABASE_JWT_SECRET is not configured on the server."
                )
            verify_key: Any = self._jwt_secret
            algorithm = "HS256"
        else:
            verify_key, algorithm = await self._resolve_jwks_key(token)

        try:
            payload = jwt.decode(
                token,
                verify_key,
                algorithms=[algorithm],
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

    async def _resolve_jwks_key(self, token: str) -> tuple[Any, str]:
        """Return ``(public_key, algorithm)`` for an asymmetrically signed token.

        The JWKS client does blocking network I/O, so it runs in a worker
        thread. The algorithm comes from the matching published key and is
        checked against an allowlist.
        """
        try:
            jwks_client = self._get_jwks_client()
        except Exception:
            raise ValueError("Unable to reach JWKS endpoint.")

        try:
            signing_key = await asyncio.to_thread(
                jwks_client.get_signing_key_from_jwt, token
            )
        except Exception:
            # Key rotation or stale cache: refresh once with a fresh client.
            self._jwks_client = None
            self._jwks_fetch_time = None
            try:
                jwks_client = self._get_jwks_client()
                signing_key = await asyncio.to_thread(
                    jwks_client.get_signing_key_from_jwt, token
                )
            except Exception as exc:
                raise ValueError("Invalid token: unable to find signing key.") from exc

        algorithm = getattr(signing_key, "algorithm_name", None)
        if algorithm not in _ALLOWED_ALGORITHMS:
            raise ValueError(
                f"Unsupported token signing algorithm: {algorithm or 'unknown'}"
            )
        return signing_key.key, algorithm

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
