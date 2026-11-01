"""Health check routes."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health() -> dict:
    """Return the service health status.

    This endpoint does not depend on any external system or secret, so it
    remains available during early development. Provider configuration
    status is reported without exposing secrets.
    """
    settings = get_settings()
    return {
        "status": "ok",
        "service": "careertwin-api",
        "environment": settings.environment,
        "providers": {
            "database": "configured" if settings.database_url else "unconfigured",
            "supabase": "configured" if settings.supabase_url else "unconfigured",
            "llm": "configured" if settings.llm_api_key or settings.llm_provider == "fake" else "unconfigured",
            "embeddings": "configured" if getattr(settings, "embedding_api_key", None) or settings.embedding_provider == "fake" else "unconfigured",
        },
    }
