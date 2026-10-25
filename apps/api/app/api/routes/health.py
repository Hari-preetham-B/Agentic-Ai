"""Health check routes."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health() -> dict:
    """Return the service health status.

    This endpoint does not depend on any external system or secret, so it
    remains available during early development.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": "careertwin-api",
        "environment": settings.environment,
    }
