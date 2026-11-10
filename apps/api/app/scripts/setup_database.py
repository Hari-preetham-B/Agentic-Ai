"""One-command database setup: migrate, seed reference data, seed evidence.

Usage (from apps/api, with DATABASE_URL set in .env):

    python -m app.scripts.setup_database

Safe to re-run: migrations are incremental and both seeds are idempotent.
It never drops or resets existing user data.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from app.core.config import get_settings


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    api_dir = Path(__file__).resolve().parents[2]
    config = Config(str(api_dir / "alembic.ini"))
    config.set_main_option("script_location", str(api_dir / "alembic"))
    command.upgrade(config, "head")


def main() -> int:
    settings = get_settings()
    if not settings.database_url:
        print(
            "DATABASE_URL is not set. Put it in apps/api/.env (or the repository "
            "root .env), e.g.\n"
            "  DATABASE_URL=postgresql+asyncpg://postgres:<password>@<host>:5432/postgres",
            file=sys.stderr,
        )
        return 2

    print("1/3 Applying database migrations ...")
    _run_migrations()

    from app.scripts.seed_evidence import seed_evidence
    from app.scripts.seed_reference_data import seed_reference_data

    print("2/3 Seeding careers, skills, resources and interview questions ...")
    reference = asyncio.run(seed_reference_data())
    print("    ", reference)

    print("3/3 Seeding the evidence corpus ...")
    evidence = asyncio.run(seed_evidence())
    print("    ", evidence)

    from app.core.diagnostics import collect_diagnostics

    info = asyncio.run(collect_diagnostics())
    print("\nDone. Database:", info["database"])
    for problem in info["problems"]:
        print(" - note:", problem)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
