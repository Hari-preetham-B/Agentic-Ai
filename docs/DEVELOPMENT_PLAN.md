# Development Plan — CareerTwin

## Phase 1 — Foundation (implemented)
**Goal:** Establish the repository structure, frontend shell, backend shell,
shared contracts, environment configuration, source-of-truth documentation,
basic tooling, and health-check functionality.

**Outcomes:**
- Monorepo: `apps/web`, `apps/api`, `packages/shared`, `docs/`
- Next.js + Tailwind + Motion frontend shell
- FastAPI + Pydantic Settings backend shell
- `GET /health`
- All nine source-of-truth documents
- Environment templates (server-side secrets only)
- Basic validation: lint, type check, build, tests, `/health`

**Dependencies:** None.

## Phase 2 — Profile and onboarding (implemented)
**Goal:** Create the canonical structured student profile that all future
CareerTwin intelligence operates on. Support manual profile creation and
resume upload, with validation, review, and confirmation.

**Outcomes:**
- PostgreSQL/Supabase connected via SQLAlchemy 2.x async + asyncpg
- Alembic initial migration: `profiles`, `education`, `skills`, `projects`,
  `experience`, `career_goals` (with FKs, cascading deletes, UUID PKs,
  timestamps, DB constraints)
- Pydantic domain schemas (request/response/detail); SQLAlchemy models never
  exposed directly
- Profile service: CRUD, deterministic validation, confirmation lifecycle
  (DRAFT → REVIEW → CONFIRMED)
- Profile API: CRUD, detail, validation, confirmation, child-record endpoints
- Resume parser (PDF/DOCX/TXT) behind `ResumeParser` protocol; 10 MB limit;
  filename sanitization; no OCR, no LLM
- `ProfileExtractor` protocol + temporary deterministic mock (marked temporary;
  no LLM SDK)
- `/profiles/extract-resume` and `/profiles/extract-resume/draft` endpoints
- Typed frontend API client layer
- Real onboarding flow: start → manual/resume → profile → review → confirm →
  `/app/twin`
- `/app/twin` displays the confirmed profile

**Dependencies:** Phase 1.

## Phase 3 — Agentic core (next)
**Goal:** The application-level orchestrator and selective agent invocation.

**Outcomes:**
- Application orchestrator
- LangGraph stateful workflows (foundation)
- LLM provider abstraction
- Agent execution traces (`agent_runs`, `agent_events`)

**Dependencies:** Phase 1, Phase 2.

## Phase 4 — Career intelligence
**Goal:** Career path analysis and skill-gap mathematics.

**Outcomes:**
- Career Agent
- Skill Gap Agent
- Skill-gap mathematics (deterministic service)
- Career paths data

**Dependencies:** Phase 2, Phase 3.

## Phase 5 — Evidence / RAG
**Goal:** Evidence-aware information verification.

**Outcomes:**
- Ingestion, chunking, embeddings
- PostgreSQL + pgvector
- Semantic + metadata retrieval
- Evidence Agent
- Claim classes: SUPPORTED / INFERRED / UNCERTAIN / CONTRADICTED
- Confidence engine (not LLM self-reported)

**Dependencies:** Phase 3.

## Phase 6 — Learning roadmap
**Goal:** Personalized learning plans.

**Outcomes:**
- Learning Agent
- Learning plans and learning items
- Evidence-backed resources and milestones

**Dependencies:** Phase 4, Phase 5.

## Phase 7 — Interview lab
**Goal:** Adaptive interview preparation.

**Outcomes:**
- Interview Agent
- Interview sessions and answers
- Interview evaluation

**Dependencies:** Phase 2, Phase 3.

## Phase 8 — UI / motion polish
**Goal:** Refine the premium dark technical/editorial UI.

**Outcomes:**
- Section reveals, navigation transitions
- Asymmetric editorial compositions
- Floating informational panels
- Selective 3D for visual experiences

**Dependencies:** All prior phases.

## Phase 9 — Testing and deployment
**Goal:** Full test coverage and deployment configuration.

**Outcomes:**
- Frontend unit tests
- Backend unit tests, API tests, Pydantic validation tests
- Agent workflow tests
- Evidence retrieval tests
- Claim classification tests
- Confidence-engine tests
- Integration and end-to-end tests
- Security / authorization tests
- Vercel (Next.js) and Render (FastAPI) configuration

**Dependencies:** All prior phases.
