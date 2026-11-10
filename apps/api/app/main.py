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
        "CareerTwin backend: profiles, career intelligence, learning roadmaps, "
        "adaptive interviews, evidence verification and agent orchestration."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS configuration
settings = get_settings()
allowed_origins = [
    o.strip().rstrip("/") for o in settings.cors_origins.split(",") if o.strip()
]

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


@app.on_event("startup")
async def log_startup_diagnostics() -> None:
    """Log configuration problems that otherwise surface as opaque 500s."""
    import logging

    from app.core.diagnostics import collect_diagnostics

    log = logging.getLogger("careertwin.startup")
    info = await collect_diagnostics()
    log.info(
        "CareerTwin API | env=%s auth=%s db=%s llm=%s",
        info["environment"], info["auth_mode"], info["database"]["status"], info["llm"]["mode"],
    )
    for hint in info["problems"]:
        log.warning("SETUP PROBLEM: %s", hint)


@app.on_event("shutdown")
async def shutdown() -> None:
    await dispose_engine()
