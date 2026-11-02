"""FastAPI application factory and entry point."""

from fastapi import FastAPI

from app.api.routes import (
    agent_runs_router,
    auth_router,
    careers_router,
    careertwin_router,
    evidence_router,
    health,
    interviews_router,
    learning_router,
    profiles_router,
    resume_router,
)
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import dispose_engine
from app.core.error_handling import register_error_handlers, StructuredErrorMiddleware
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="CareerTwin API",
    description=(
        "Career intelligence backend — foundation stage. Profile and onboarding "
        "capability implemented. No AI agents implemented yet."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration
settings = get_settings()
allowed_origins = ["http://localhost:3000"]
if settings.environment == "production":
    allowed_origins = [o for o in allowed_origins if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handling
app.add_middleware(StructuredErrorMiddleware)
register_error_handlers(app)

app.include_router(health.router)
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(resume_router)
app.include_router(agent_runs_router)
app.include_router(careers_router)
app.include_router(careertwin_router)
app.include_router(evidence_router)
app.include_router(interviews_router)
app.include_router(learning_router)


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": "careertwin-api",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.on_event("shutdown")
async def shutdown() -> None:
    await dispose_engine()
