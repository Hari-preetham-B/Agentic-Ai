"""Authentication package."""

from app.core.auth.dependency import (  # noqa: F401
    AuthenticatedUser,
    get_auth_provider,
    get_current_user,
    set_auth_provider,
)
from app.core.auth.provider import (  # noqa: F401
    AuthProvider,
    AuthenticatedUser as AuthenticatedUserModel,
    FakeAuthProvider,
)

__all__ = [
    "AuthProvider",
    "AuthenticatedUser",
    "FakeAuthProvider",
    "get_auth_provider",
    "get_current_user",
    "set_auth_provider",
]
