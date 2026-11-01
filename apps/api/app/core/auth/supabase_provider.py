"""Supabase authentication provider.

Validates Supabase JWT tokens using the project's JWT secret.
This is a production-ready provider that will be activated when
Supabase credentials are configured.

For development and testing, FakeAuthProvider is used instead.
"""

from __future__ import annotations

from typing import Any

from app.core.auth.provider import AuthenticatedUser


class SupabaseAuthProvider:
    """Auth provider that validates Supabase JWT tokens.

    Uses the Supabase project's JWT secret to verify token signatures.
    Activated when SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are configured.
    """

    provider_name = "supabase"

    def __init__(
        self,
        supabase_url: str,
        supabase_service_role_key: str,
        jwt_secret: str | None = None,
    ) -> None:
        self.supabase_url = supabase_url
        self.supabase_service_role_key = supabase_service_role_key
        self.jwt_secret = jwt_secret

    async def validate_token(self, token: str) -> AuthenticatedUser:
        """Validate a Supabase JWT token.

        Uses PyJWT to verify the token signature and extract claims.
        """
        import jwt

        if not token:
            raise ValueError("Missing authentication token.")

        # Decode and verify the JWT.
        try:
            # Supabase JWTs are signed with the project's JWT secret.
            # The secret can be obtained from the Supabase dashboard.
            if self.jwt_secret:
                payload = jwt.decode(
                    token,
                    self.jwt_secret,
                    algorithms=["HS256"],
                    audience="authenticated",
                )
            else:
                # Without a JWT secret, we can't verify locally.
                # This would require calling Supabase's auth endpoint.
                raise ValueError("JWT secret not configured.")

            user_id = payload.get("sub")
            if not user_id:
                raise ValueError("Invalid token: missing subject.")

            email = payload.get("email")
            return AuthenticatedUser(
                user_id=user_id,
                email=email,
                metadata={"provider": "supabase"},
            )
        except jwt.ExpiredSignatureError:
            raise ValueError("Token has expired.")
        except jwt.InvalidTokenError as exc:
            raise ValueError(f"Invalid token: {exc}")


__all__ = ["SupabaseAuthProvider"]
