"""Centralized application configuration using Pydantic Settings.

Environment variables are read here, in one place, and nowhere else.
All optional secrets default to None so the application can start during
development without production credentials configured.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration.

    Fields with defaults are development-safe. Secrets (Supabase service role
    key, LLM API key, database URL) are intentionally optional and default to
    None so the application remains importable without them.
    """

    # Environment
    environment: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Supabase (server-side only)
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_jwt_secret: str | None = None

    # Database (PostgreSQL via SQLAlchemy async + asyncpg)
    # Example: postgresql+asyncpg://postgres:password@localhost:5432/careertwin
    database_url: str | None = None

    # LLM provider (server-side only). Provider choice is intentionally not locked.
    llm_provider: str | None = None
    llm_model: str | None = None
    llm_api_key: str | None = None

    # Embedding provider (server-side only)
    embedding_provider: str | None = None
    embedding_model: str | None = None
    embedding_api_key: str | None = None
    embedding_dimension: int = 384

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
