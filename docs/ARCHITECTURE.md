# Architecture — CareerTwin

## Data flow

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

## Implemented foundation vs future architecture

### Implemented in this stage (foundation + profile/onboarding)
- Next.js frontend shell with App Router, Tailwind CSS, and Motion
- Route structure: `/`, `/auth/*`, `/onboarding/*`, `/app/*`
- FastAPI backend shell with centralized Pydantic Settings config
- `GET /health` health endpoint and FastAPI docs (`/docs`)
- Environment templates (server-side secrets only)
- Source-of-truth documentation
- Git repository on `feat/foundation`

**Profile + Onboarding (Phase 2):**
- SQLAlchemy 2.x async + asyncpg persistence against PostgreSQL/Supabase
- Alembic initial migration: `profiles`, `education`, `skills`, `projects`,
  `experience`, `career_goals`
- Pydantic domain schemas (request/response/detail)
- Profile service layer: CRUD, validation, confirmation
- Profile API: `POST/GET/PUT/DELETE /profiles/{id}`, detail endpoint,
  validation, confirmation
- Child-record endpoints: education, skills, projects, experience,
  career-goals
- Resume parser service (PDF via PyMuPDF, DOCX via python-docx, TXT)
- Profile extraction boundary (`ProfileExtractor` protocol + temporary
  deterministic mock)
- `/profiles/extract-resume` (raw text) and `/profiles/extract-resume/draft`
  (structured draft) endpoints
- Typed frontend API client layer (`src/lib/api/client.ts`)
- Real onboarding flow: start → choose manual/resume → profile → review →
  confirm → `/app/twin`
- `/app/twin` displays the confirmed profile

### Future architecture (not yet implemented)
- Six specialized agents (Profile, Career, Skill Gap, Learning, Interview,
  Evidence) — all implemented
- Application-level orchestrator and LangGraph stateful workflows
- LLM provider abstraction (`LLMProvider` protocol)
- Embedding provider abstraction (`EmbeddingProvider` protocol)
- Supabase pgvector, Auth, and Storage (application data schema implemented;
  Auth/RLS future)
- RAG / evidence pipeline (Phase 5 — implemented)
- Resume semantic extraction via LLM (currently deterministic mock)
- Interview evaluation, skill-gap algorithms, career recommendations,
  confidence calculations

## Frontend / backend responsibilities

### Frontend (Next.js)
- UI presentation and user interaction
- Route structure and navigation shell
- Form input capture (no business logic)
- Calling backend APIs over HTTP
- Never holds provider API keys or the Supabase service role key

### Backend (FastAPI)
- HTTP API surface
- Centralized configuration (Pydantic Settings)
- Deterministic application services (validation, storage, calculations,
  retrieval, confidence, authorization, persistence, traces)
- Agent orchestration (future)
- Identity validation and authorization (future)
- Holds all provider secrets and the Supabase service role key server-side

## Provider abstraction
Agents must eventually depend on an application-level provider abstraction
rather than directly importing Groq, Gemini, OpenAI, or another vendor SDK.

Conceptual interface:

```python
class LLMProvider(Protocol):
    async def generate(
        self,
        messages: list[dict],
        *,
        tools: list[dict] | None = None,
        response_schema: type | None = None,
    ) -> LLMResponse:
        ...
```

This allows multiple providers later. Provider-specific secrets remain
server-side. The frontend never receives provider API keys.

## Deterministic vs agentic responsibilities

### Deterministic services (not agents)
- validation
- storage
- calculations
- skill-gap mathematics
- retrieval
- confidence calculation
- authorization
- state persistence
- trace persistence

### LLMs / agents
- reasoning
- planning
- interpretation
- adaptive generation
- evaluation
- claim analysis

Never implement "everything as an agent."

## Authentication architecture (future)
- Supabase Auth
- PostgreSQL Row Level Security
- FastAPI-side identity validation and authorization
Not implemented in this stage.

## Future deployment architecture
- Vercel for Next.js
- Render for FastAPI
- Supabase for database/auth/storage
Nothing deployed in this stage.

## Data ownership
The CareerTwin (user's professional state) is owned by the user and stored
in Supabase PostgreSQL. Agent-derived analysis and evidence references are
linked to the owning profile.

## Profile persistence
Profiles and their child records (education, skills, projects, experience,
career goals) are stored in PostgreSQL via SQLAlchemy 2.x async. Every child
record references `profiles.id` with a foreign key and cascading delete.
Profile status follows a controlled lifecycle: `DRAFT → REVIEW → CONFIRMED`.
Only an explicit user confirmation sets `CONFIRMED`; extracted resume data is
never auto-confirmed.

## Document processing boundary
Resume text extraction sits behind the `ResumeParser` protocol. Supported
formats: PDF (PyMuPDF), DOCX (python-docx), TXT. Validation (file type, size
≤ 10 MB, filename sanitization) happens before parsing. Parsing returns raw
text only — no semantic extraction and no LLM calls in this phase.

## Profile extraction boundary
The `ProfileExtractor` protocol turns raw document text into a structured
`ProfileDraft`. This phase provides a temporary deterministic mock (clearly
marked); the future Profile Agent replaces it. The rest of the application
depends on this abstraction, never directly on an LLM SDK. The draft is not
persisted as confirmed user data until the user reviews and confirms.

## Validation service
A deterministic profile validation service checks structural integrity and
business rules (name present, at least one skill, at least one career goal
before confirmation, valid dates, valid enum/source values, no duplicate
skills). It returns structured `{ valid, errors, warnings }` results. Errors
block confirmation; warnings do not block saving.

## API client boundary
The frontend uses a typed API client layer (`src/lib/api/client.ts`) so
components never scatter raw `fetch()` calls. The client mirrors backend
Pydantic schemas and handles errors (network, validation, upload, server).
Provider API keys and the Supabase service role key never reach the frontend.

## Security boundaries
- Provider API keys and Supabase service role key: server-side only
- Frontend: only `NEXT_PUBLIC_*` variables, no secrets
- Authentication boundary: future Supabase Auth + RLS
- No secrets committed to git

## Agent execution trace concept (future)
Every agent run produces an inspectable execution trace stored in
`agent_runs` / `agent_events`. Traces make agent behavior auditable and are
not decorative animations.

## Evidence intelligence (Phase 5)
Evidence intelligence uses PostgreSQL pgvector for semantic retrieval. The
pipeline is:

```
Generated Response
  → Claim Extraction (ClaimExtractionService)
  → Evidence Retrieval (EvidenceRetriever — pgvector cosine similarity)
  → Claim/Evidence Comparison (ClaimVerificationService)
  → Contradiction Detection
  → Confidence Engine (deterministic)
  → SUPPORTED / INFERRED / UNCERTAIN / CONTRADICTED
```

Embeddings are abstracted behind `EmbeddingProvider` (similar to `LLMProvider`).
A `FakeEmbeddingProvider` is provided for tests. pgvector's `<=>` operator
is used for native cosine-distance search in production (PostgreSQL). SQLite
tests use a Python cosine-similarity fallback.

Source hierarchy (strongest → weakest):
1. USER_CONFIRMED
2. USER_DOCUMENT
3. CURATED_KNOWLEDGE
4. RETRIEVED_EXTERNAL
5. LLM_INFERENCE

Confidence is NEVER derived from LLM self-assessment. It is computed
deterministically by `ConfidenceEngine` from observable signals:
source reliability, evidence hierarchy, similarity, support strength,
contradiction strength, freshness, and directness.
