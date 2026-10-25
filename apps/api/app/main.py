"""FastAPI application factory and entry point."""

from fastapi import FastAPI

from app.api.routes import health
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="CareerTwin API",
    description="Career intelligence backend — foundation stage. No AI agents implemented yet.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.include_router(health.router)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": "careertwin-api",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }
