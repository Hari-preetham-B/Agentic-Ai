# CareerTwin Backend

Foundation-stage FastAPI backend for the CareerTwin project.

## Status

Foundation stage only. No AI agents, RAG, or authentication implemented yet.

## Structure

```text
apps/api/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI application factory
│   ├── core/
│   │   ├── config.py      # Pydantic Settings (centralized config)
│   │   └── logging.py     # Logging configuration
│   ├── api/
│   │   └── routes/
│   │       └── health.py  # GET /health
│   ├── models/            # Future database/domain models
│   ├── schemas/           # Future Pydantic schemas
│   ├── services/          # Future deterministic application services
│   └── agents/            # Future agent architecture (placeholder only)
├── tests/
│   └── test_health.py
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

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints

- `GET /` — service meta
- `GET /health` — structured health check
- `GET /docs` — FastAPI interactive documentation
- `GET /redoc` — ReDoc documentation

## Testing

```bash
pytest
```

## Security

No real secrets are committed. Provider API keys and the Supabase service role
key must remain server-side only.
