# CareerTwin

CareerTwin is an AI-powered career intelligence system for students. It
maintains an evolving structured representation of a student's professional
state called the **CareerTwin**.

## Status

**Profile + Onboarding (Phase 2) implemented.** This release adds a strongly
typed, validated, persisted, and confirmable CareerTwin profile, plus resume
upload (PDF/DOCX/TXT) with deterministic text extraction and a structured
draft for review.

No AI agents, LangGraph, RAG, or authentication implemented yet.

## Architecture summary

```
Browser
  ↓
Next.js (http://localhost:3000)
  ↓
FastAPI (http://localhost:8000)
  ↓
Application Orchestrator (future)
  ↓
LangGraph workflows (future)
  ↓
Specialized Agents (future)
  ↓
Services / Tools
  ↓
Supabase PostgreSQL + pgvector + Storage (future)
```

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, Motion.
- **Backend:** FastAPI, Pydantic, Pydantic Settings, pytest.
- **Database (planned):** Supabase, PostgreSQL, pgvector.
- **Authentication (planned):** Supabase Auth + PostgreSQL RLS.

## Repository structure

```text
careertwin/
├── apps/
│   ├── web/              # Next.js frontend (port 3000)
│   └── api/              # FastAPI backend (port 8000)
├── packages/
│   └── shared/           # Shared frontend/backend contracts
├── docs/                 # Source-of-truth specifications
├── .github/workflows/    # CI
├── .env.example          # Root environment template
├── .gitignore
└── README.md
```

## Local development

### Frontend

```bash
cd apps/web
npm install
npm run dev        # http://localhost:3000
```

### Backend

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e .
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Health check

```bash
curl http://localhost:8000/health
```

## Environment setup

Copy `.env.example` to `.env` at the root (and/or in `apps/web` and `apps/api`)
and fill in values. Provider API keys and the Supabase service role key are
server-side only — never expose them through `NEXT_PUBLIC_*`.

## Current implementation status

| Area | Status |
|------|--------|
| Repository structure | ✅ |
| Frontend shell (Next.js + Tailwind + Motion) | ✅ |
| Backend shell (FastAPI + Pydantic Settings) | ✅ |
| Shared package | ✅ (contract boundary defined) |
| Source-of-truth docs | ✅ |
| `/health` endpoint | ✅ |
| PostgreSQL/Supabase + SQLAlchemy + Alembic | ✅ |
| Profile CRUD + validation + confirmation | ✅ |
| Resume upload (PDF/DOCX/TXT) + draft | ✅ |
| Onboarding flow + `/app/twin` | ✅ |
| Authentication | ❌ later phase |
| AI agents | ❌ later phase |
| RAG / pgvector | ❌ later phase |
| Resume semantic extraction | ❌ later phase |

## Future roadmap

See `docs/DEVELOPMENT_PLAN.md` for the planned implementation phases.

## Security

No real secrets are committed. Never commit `.env` files or provider keys.
