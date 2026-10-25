# CareerTwin Backend

Profile + onboarding stage. FastAPI backend with PostgreSQL persistence via
SQLAlchemy 2.x async + asyncpg. No AI agents, RAG, or authentication
implemented yet.

## Structure

```text
apps/api/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI application factory
│   ├── core/
│   │   ├── config.py      # Pydantic Settings (centralized config)
│   │   ├── database.py    # async SQLAlchemy engine/session
│   │   └── logging.py     # Logging configuration
│   ├── api/
│   │   └── routes/
│   │       ├── health.py  # GET /health
│   │       ├── profiles.py  # Profile CRUD, validation, confirmation
│   │       └── resume.py    # Resume extraction + draft
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base.py        # Base + shared column conventions
│   │   └── profile.py     # Profile, Education, Skill, Project,
│   │                       Experience, CareerGoal
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── profile.py     # Pydantic request/response/detail schemas
│   ├── services/
│   │   ├── __init__.py
│   │   ├── profile_service.py   # Persistence + validation + confirmation
│   │   ├── validation.py        # Deterministic profile validation
│   │   ├── resume_parser.py     # PDF/DOCX/TXT text extraction
│   │   └── profile_extractor.py # ProfileExtractor protocol + mock
│   └── agents/            # Future agent architecture (placeholder only)
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_initial_schema.py  # Initial migration
├── tests/
│   ├── conftest.py        # in-memory SQLite fixture
│   ├── test_health.py
│   ├── test_profile.py
│   └── test_resume.py
├── alembic.ini
├── pyproject.toml
└── README.md
```

## Local development

```bash
# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env

# Provide DATABASE_URL (PostgreSQL via asyncpg) in .env, e.g.:
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/careertwin

# Run database migrations
alembic upgrade head

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

If `DATABASE_URL` is not set, the app starts against a shared in-memory
SQLite database so it stays importable and testable without PostgreSQL.

## Endpoints

- `GET /` — service meta
- `GET /health` — structured health check
- `GET /docs` — FastAPI interactive documentation
- `GET /redoc` — ReDoc documentation
- Profile and resume endpoints (see `docs/API_SPEC.md`)

## Testing

```bash
pytest
```

Tests run against an in-memory SQLite database; no real PostgreSQL required.

## Security

No real secrets are committed. Provider API keys and the Supabase service role
key must remain server-side only.
