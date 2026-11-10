# CareerTwin

CareerTwin is an agentic career-intelligence and evidence-aware assistant for students. It builds a structured
profile (the **CareerTwin**), matches it against curated careers with deterministic scoring, generates a
prerequisite-ordered learning roadmap, runs adaptive mock interviews, and shows how trustworthy each AI-generated
claim is (SUPPORTED / INFERRED / UNCERTAIN / CONTRADICTED) with inspectable evidence and persisted agent traces.

| Layer | Technology |
|---|---|
| Web (`apps/web`, port 3000) | Next.js 16, React 19, TypeScript, Tailwind, Framer Motion |
| API (`apps/api`, port 8000) | FastAPI, Pydantic, SQLAlchemy 2 (async), Alembic |
| Data / auth | Supabase PostgreSQL + pgvector, Supabase Auth (JWT) |
| Agents | Seven agents on LangGraph with a custom orchestrator and typed tools |
| AI | Gemini when configured, deterministic fake providers otherwise |

## Quick start

Prerequisites: Python 3.11+, Node 20+, a Supabase project (or any PostgreSQL with the `vector` extension).

### 1. Configure

Copy `.env.example` to `.env` in the repository root and fill it in. **One root file configures both apps.**

* Supabase -> Project Settings -> API: `NEXT_PUBLIC_SUPABASE_URL` and `SUPABASE_URL` (same value),
  `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, and `SUPABASE_SECRET_KEY`.
* Supabase -> Connect: copy the **Session pooler** connection string into `DATABASE_URL`, change the scheme to
  `postgresql+asyncpg://`, and URL-encode special characters in the password. (The "direct" host is IPv6-only on many
  plans and fails on home networks.)
* `LLM_API_KEY` for Gemini is optional. Without it the app runs on the deterministic fallback provider.
* In Supabase -> Database -> Extensions, make sure `vector` is enabled.

### 2. Backend

```bash
cd apps/api
python -m venv .venv
# Windows: .venv\Scripts\activate      macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
python -m app.scripts.setup_database     # migrations + reference data + evidence corpus (safe to re-run)
uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000/health/diagnostics>. It lists exactly what is missing (database, migrations, seeds, auth
mode, LLM mode) and never prints secrets. `/docs` shows the interactive API.

### 3. Frontend

```bash
cd apps/web
npm install
npm run dev
```

Open <http://localhost:3000>. Sign up, choose manual entry or resume upload (PDF, DOCX, TXT), review and confirm
the profile, and the Twin, Careers, Skills, Roadmap, Interview and Trust pages become available.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Every API call returns **401** | `SUPABASE_URL` differs from the web app's project, or the token is legacy HS256: set `SUPABASE_JWT_SECRET`. If you have no Supabase configured at all, leave all Supabase variables empty (development fake auth) and make sure `ENVIRONMENT` is not `production`. |
| Pages fail with **500 / "no such table"** | `DATABASE_URL` is not loaded and the API is using an empty in-memory database. Check `/health/diagnostics`, then run `python -m app.scripts.setup_database`. |
| Careers list is empty | Reference data is not seeded: run the setup command above. |
| "Cannot connect to the database" | Wrong host or password, or the direct Supabase host on an IPv4-only network. Use the Session pooler string. |
| `prepared statement ... already exists` | You used the transaction pooler (port 6543). The API handles this; for migrations prefer port 5432. |
| Browser CORS error | Open the app at `localhost:3000` or add your origin to `CORS_ORIGINS`. |
| Sign-up works but you cannot sign in | Email confirmation is on and `SUPABASE_SECRET_KEY` is missing. Set it (with `AUTO_CONFIRM_SIGNUPS=true`) or confirm the email. |
| `next build` fails fetching fonts | The build downloads Google Fonts; it needs internet access. |
| Gemini calls fail | Check `LLM_API_KEY` and `LLM_MODEL` (set `LLM_FALLBACK_MODELS`). Agents fall back to deterministic output, and the interview evaluator reports which evaluator was used. |

## Testing

```bash
cd apps/api && python -m pytest          # 188 pass; 32 skip (live Supabase/Gemini smoke tests)
cd apps/web && npx tsc --noEmit && npx eslint && npm run build
```

Tests run on SQLite and use no external services. Live smoke tests run only when their credentials are present.

## How it works

* **Deterministic first.** Skill matching, career fit, roadmap sequencing (dependency graph, cycle detection,
  topological order), interview difficulty (>= 0.80 up, <= 0.45 down), and claim confidence are plain code. LLMs never
  set scores or confidence.
* **Confidence** = `quality*0.20 + agreement*0.25 + directness*0.45 + freshness*0.10 - max(contradiction)*0.35`,
  clamped to [0, 1]. Thresholds: SUPPORTED >= 0.70, INFERRED >= 0.40, UNCERTAIN >= 0.10, otherwise CONTRADICTED.
* **Agents** (Profile, Career, Skill Gap, Learning, Interview, Evidence, CareerTwin) run only when a capability needs
  them. Every run persists `RUN_STARTED`, `TOOL_STARTED/COMPLETED`, `AGENT_*` and `RUN_*` events, which the Twin page
  shows. Chain-of-thought is never stored.
* **Resume onboarding** parses text deterministically into a draft you review. With a Gemini key the model also
  structures it, and every item is validated; any failure falls back to the deterministic parser. Skill levels are
  never guessed.
* **Ownership.** Every user-owned route checks the authenticated user. The API connects as the database owner role,
  which bypasses Postgres RLS, so application-level checks are what protect data. RLS policies exist as defence in
  depth only.

## Known limitations

* Evidence retrieval uses the deterministic fallback embedder end to end (seed script, search, and agent). Gemini
  embeddings are configurable but not wired into evidence retrieval; enabling them requires re-embedding the corpus.
* No OCR: scanned or image-only resumes cannot be read.
* The default `gemini-3.8-flash` model name is configurable and has not been verified against a live key.
  Set `LLM_MODEL` / `LLM_FALLBACK_MODELS` to models available to your key.
* The web UI has been type-checked, linted and production-built, and its API contracts checked against live
  responses, but it has not been exercised in a real browser session.
