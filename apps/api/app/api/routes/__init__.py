"""API route package."""

from app.api.routes.profiles import router as profiles_router
from app.api.routes.resume import router as resume_router

__all__ = ["profiles_router", "resume_router"]
