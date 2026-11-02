# External Providers — CareerTwin

This document describes the external services required to run CareerTwin
in production. No real credentials are included.

## Current Development Provider: Google Gemini

CareerTwin uses Google Gemini as the current development LLM and embedding
provider.

### LLM
- Provider: `gemini`
- Model: `gemini-3.8-flash`
- API key environment variable: `LLM_API_KEY`
- Backend-only (never exposed to frontend)

### Embeddings
- Provider: `gemini`
- Model: `gemini-embedding-2`
- API key environment variable: `EMBEDDING_API_KEY`
- Output dimension: `384`
- Environment variable: `EMBEDDING_DIMENSION=384`
- Backend-only (never exposed to frontend)

### Important Notes
- The application remains provider-independent. Gemini is the current
  development provider, but the architecture supports swapping providers
  without changing agent code.
- Automated tests use `FakeLLMProvider` and `FakeEmbeddingProvider`.
  No real API calls are made during normal test runs.
- Changing embedding models requires re-embedding existing evidence vectors
  because embedding spaces are not interchangeable.
- The pgvector column uses `Vector(384)`. The production embedding model
  must produce exactly 384 dimensions unless the schema is intentionally
  changed via migration.

## Supabase

### Required credentials

1. **Project URL** (`SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`)
   - Where to obtain: Supabase Dashboard → Settings → API → Project URL
   - Secret: No (public, safe for browser)
   - Used by: Frontend (browser) and Backend (server)

2. **Publishable/Anon Key** (`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` / `SUPABASE_PUBLISHABLE_KEY`)
   - Where to obtain: Supabase Dashboard → Settings → API → anon/public key
   - Secret: No (public, safe for browser)
   - Used by: Frontend (browser) and Backend (server)

3. **Secret Key** (`SUPABASE_SECRET_KEY`)
   - Where to obtain: Supabase Dashboard → Settings → API → service_role key
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only

4. **JWT Secret** (`SUPABASE_JWT_SECRET`)
   - Where to obtain: Supabase Dashboard → Settings → API → JWT Secret
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only
   - **Legacy**: Supabase now uses asymmetric JWT signing keys. The backend
     verifies access tokens using the Supabase JWKS endpoint instead of this
     shared secret. `SUPABASE_JWT_SECRET` is kept for backward compatibility
     but is no longer the primary verification mechanism.

### JWT Verification (JWKS)

The backend verifies Supabase Auth access tokens using the project's JWKS
endpoint, which is derived from `SUPABASE_URL`:

```
{SUPABASE_URL}/auth/v1/.well-known/jwks.json
```

Key points:
- Supabase projects use **asymmetric** JWT signing keys (ECC P-256).
- The corresponding public keys are published at the JWKS endpoint above.
- JWKS public keys are safe to retrieve — they are public verification keys.
- The backend caches JWKS data with a 5-minute TTL and refreshes on key
  rotation (unknown `kid`).
- `SUPABASE_SECRET_KEY` (service_role key) is **not** used as a JWT signing
  secret — it is a different concept for server-to-server API calls.
- Algorithm confusion is prevented: only RS256/ES256 tokens from the JWKS
  endpoint are accepted; `alg=none` is never allowed.

5. **PostgreSQL Connection URL** (`DATABASE_URL`)
   - Where to obtain: Supabase Dashboard → Settings → Database → Connection string
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only
   - Format: `postgresql+asyncpg://postgres:password@db.<ref>.supabase.co:5432/postgres`
     (must use `+asyncpg` driver for SQLAlchemy async engine)

### Database Integration

The backend connects to Supabase PostgreSQL via SQLAlchemy 2.x async + asyncpg.
Alembic manages schema migrations.

**Connection model:**
- FastAPI connects **directly** to PostgreSQL as the `postgres` role (specified in `DATABASE_URL`)
- The `postgres` role is the database owner, which **bypasses PostgreSQL RLS** by default
- `auth.uid()` returns `NULL` for FastAPI connections (no JWT claim propagation)
- RLS policies exist as defense-in-depth but are **NOT enforced** on the FastAPI connection path
- Application-layer ownership enforcement is **required** and is the effective authorization boundary

**Required extensions:**
- `pgvector` — for 384-dimensional embedding storage (created by migration `0003`)

**Migration sequence:**
1. `0001_initial_schema` — profiles, education, skills, projects, experience, career_goals, agent_runs, agent_events
2. `0002_career_knowledge` — careers, career_skills, career_tools, career_projects, career_sources
3. `0003_evidence_intelligence` — evidence_sources, evidence_documents, evidence_chunks, claims, claim_evidence (+ pgvector)
4. `0004_learning_roadmap` — learning_resources, skill_dependencies, learning_resource_skills, roadmaps, roadmap_items, roadmap_resources
5. `0005_adaptive_interview` — interview_sessions, interview_questions, interview_question_skills, interview_turns, interview_evaluations, interview_skill_results
6. `0006_row_level_security` — RLS on 15 user-owned tables

**Apply migrations:**
```bash
cd apps/api
alembic upgrade head
```

**Current Alembic head:** `0006_row_level_security`

### Application-Layer Authorization

Because FastAPI connects as the `postgres` owner role, PostgreSQL RLS does not
enforce user isolation on the application database path. Instead, the
application enforces ownership at the service layer:

- FastAPI routes use `get_current_user` dependency to validate Bearer tokens
- Profile service functions accept a `user_id` parameter and filter queries by
  `profiles.user_id == user_id`
- Child record operations verify profile ownership via join on `profiles.user_id`

This is the effective authorization boundary. RLS policies remain in the
database as defense-in-depth for connections made through the Supabase API
Gateway (where `auth.uid()` is populated from JWT claims).

**Authorization summary:**
| Check | Enforced by | Effective on FastAPI path? |
|-------|-------------|---------------------------|
| Token validation | `get_current_user` dependency | Yes |
| Profile ownership | `profile_service.py` (`user_id` filter) | Yes |
| Child record ownership | `profile_service.py` (join on `profiles.user_id`) | Yes |
| PostgreSQL RLS | `auth.uid()` policies | No (bypassed by `postgres` role) |

### Row Level Security (RLS)

Migration `0006_row_level_security` enables RLS on 15 user-owned tables:
profiles, education, skills, projects, experience, career_goals, agent_runs,
agent_events, claims, roadmaps, roadmap_items, roadmap_resources,
interview_sessions, interview_turns, interview_skill_results.

Policies use `auth.uid()` (Supabase Auth) to enforce row ownership. RLS
policies are enforced when connecting as a non-owner role (e.g. `authenticated`
via the Supabase API Gateway). Direct connections as the `postgres` superuser
bypass RLS by default (standard PostgreSQL behavior).

**40 policies** cover SELECT, INSERT, UPDATE, DELETE on user-owned tables.
Reference/curated data tables (careers, evidence_sources, learning_resources,
etc.) do not have RLS — they are readable by all authenticated roles.

### Reference Data Seed System

A deterministic seed command populates curated reference data:

```bash
cd apps/api
python -m app.scripts.seed_reference_data
```

**Behavior:**
- Connects using `DATABASE_URL` from settings
- Verifies schema is at Alembic head (`0006_row_level_security`)
- Seeds reference entities using idempotent upserts (stable identifiers)
- Commits atomically
- Reports counts per table
- Exits non-zero on failure
- Safe to rerun (idempotent — no duplicate rows)
- Does NOT touch user-owned data
- Does NOT delete existing reference data

**Seeded datasets:**

| Dataset | Count | Key fields |
|---------|-------|------------|
| careers | 8 | slug, title, domain, summary |
| career_skills | 50 | skill_name, importance, minimum_level |
| career_tools | 31 | tool_name, importance |
| career_projects | 9 | project_type, description, difficulty |
| career_sources | 9 | title, publisher, url, source_type, reliability |
| learning_resources | 13 | title, provider, resource_type, url, difficulty |
| learning_resource_skills | 18 | skill_name, relevance_score, coverage_type |
| skill_dependencies | 17 | skill, prerequisite_skill, strength |
| interview_questions | 14 | question_text, question_type, difficulty |
| interview_question_skills | 19 | skill_name, relevance_score |

**Careers seeded:**
Software Engineer, Data Analyst, Data Scientist, Machine Learning Engineer,
AI Engineer, Cybersecurity Analyst, Cloud / DevOps Engineer, Product Analyst

### Testing

**Unit tests** (default `pytest` run):
- Use SQLite in-memory database
- Use `FakeAuthProvider`, `FakeLLMProvider`, `FakeEmbeddingProvider`
- No external credentials required
- pgvector and RLS are not tested (SQLite does not support them)

**Real Supabase integration tests** (opt-in):
- Set `RUN_POSTGRES_INTEGRATION=1` environment variable
- Require real `DATABASE_URL` in `.env`
- Connect to the real Supabase PostgreSQL database
- Verify pgvector, RLS isolation, and authenticated CRUD
- Never commit `.env` or test credentials

### Local Development

### Frontend (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (.env)
```
ENVIRONMENT=development
DATABASE_URL=postgresql+asyncpg://postgres:password@db.<ref>.supabase.co:5432/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_PUBLISHABLE_KEY=<key>
SUPABASE_SECRET_KEY=<key>
SUPABASE_JWT_SECRET=<key>
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.8-flash
LLM_API_KEY=<key>
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_API_KEY=<key>
EMBEDDING_DIMENSION=384
```

### Tests
Tests use `FakeAuthProvider`, `FakeLLMProvider`, and `FakeEmbeddingProvider`.
No external credentials are required for the normal test suite.
The smoke test (`test_gemini_smoke.py`) is excluded from normal pytest runs.