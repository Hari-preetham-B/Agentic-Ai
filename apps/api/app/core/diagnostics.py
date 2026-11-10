"""Runtime configuration diagnostics (no secrets are ever returned)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app.core.config import get_settings


async def collect_diagnostics() -> dict[str, Any]:
    """Report how the API is configured and what is missing."""
    settings = get_settings()
    problems: list[str] = []

    auth_mode = "supabase" if settings.supabase_url else "fake (development only)"
    if not settings.supabase_url:
        problems.append(
            "SUPABASE_URL is not set: the API accepts only the local development "
            "token. Set SUPABASE_URL (and NEXT_PUBLIC_SUPABASE_* for the web app) "
            "to use real sign-in."
        )

    db: dict[str, Any] = {"status": "unconfigured", "migrated": False, "careers": 0, "evidence_chunks": 0}
    if not settings.database_url:
        problems.append(
            "DATABASE_URL is not set: the API is using an empty in-memory SQLite "
            "database, so most endpoints will fail. Set DATABASE_URL, then run "
            "'alembic upgrade head' and the seed scripts (see README)."
        )
    else:
        db["status"] = "error"
        try:
            from app.core.database import get_engine

            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
                db["status"] = "connected"
                try:
                    version = (await conn.execute(text("SELECT version_num FROM alembic_version"))).scalar()
                    db["migrated"] = version is not None
                    db["alembic_version"] = version
                except Exception:  # noqa: BLE001
                    await conn.rollback()
                    problems.append("Database has no alembic_version table: run 'alembic upgrade head'.")
                if db["migrated"]:
                    try:
                        db["careers"] = (await conn.execute(text("SELECT count(*) FROM careers"))).scalar() or 0
                        db["evidence_chunks"] = (
                            await conn.execute(text("SELECT count(*) FROM evidence_chunks"))
                        ).scalar() or 0
                    except Exception:  # noqa: BLE001
                        await conn.rollback()
                    if db["careers"] == 0:
                        problems.append(
                            "Reference data is not seeded: run "
                            "'python -m app.scripts.seed_reference_data'."
                        )
                    if db["evidence_chunks"] == 0:
                        problems.append(
                            "Evidence corpus is not seeded: run "
                            "'python -m app.scripts.seed_evidence'."
                        )
        except Exception as exc:  # noqa: BLE001
            problems.append(f"Cannot connect to the database ({type(exc).__name__}). Check DATABASE_URL.")

    provider = (settings.llm_provider or "fake").lower()
    llm_mode = "fake (deterministic fallback)"
    if provider == "gemini":
        if settings.llm_api_key:
            llm_mode = "gemini"
        else:
            problems.append("LLM_PROVIDER=gemini but LLM_API_KEY is empty: using the fake provider.")

    return {
        "environment": settings.environment,
        "auth_mode": auth_mode,
        "database": db,
        "llm": {"mode": llm_mode},
        "problems": problems,
    }
