"""Centralized application configuration using Pydantic Settings.

Environment variables are read here, in one place, and nowhere else.
All optional secrets default to None so the application can start during
development without production credentials configured.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Fields with defaults are development-safe. Secrets (Supabase secret key,
    LLM API key, database URL) are intentionally optional and default to
    None so the application remains importable without them.
    """

    # Environment
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Supabase (server-side only)
    supabase_url: str | None = None
    supabase_publishable_key: str | None = None
    supabase_secret_key: str | None = None
    supabase_jwt_secret: str | None = None
    # When true (default outside production), accounts created through
    # POST /auth/signup are confirmed immediately instead of waiting for the
    # Supabase confirmation email. Set AUTO_CONFIRM_SIGNUPS=false in
    # production to enforce real email verification.
    auto_confirm_signups: bool = True

    # Database (PostgreSQL via SQLAlchemy async + asyncpg)
    # Example: postgresql+asyncpg://postgres:password@db.supabase.co:5432/postgres
    database_url: str | None = None

    # LLM provider (server-side only). Provider choice is intentionally not locked.
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None
    # Comma-separated models tried in order when the primary model is
    # overloaded or unavailable (e.g. "gemini-3-flash-preview,gemini-3.1-flash-lite").
    llm_fallback_models: str | None = None

    # Embedding provider (server-side only)
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_dimension: int = 384

    # Optional, disabled by default: exposes evidence ingestion over HTTP.
    # Production data should be ingested through the seed command instead.
    enable_evidence_ingest_api: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance."""
    return Settings()


def get_settings_no_cache() -> Settings:
    """Return a fresh settings instance (useful for tests)."""
    return Settings()
