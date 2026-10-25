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

### Implemented in this stage (foundation)
- Next.js frontend shell with App Router, Tailwind CSS, and Motion
- Route structure: `/`, `/auth/*`, `/onboarding/*`, `/app/*`
- FastAPI backend shell with centralized Pydantic Settings config
- `GET /health` health endpoint and FastAPI docs (`/docs`)
- Environment templates (server-side secrets only)
- Source-of-truth documentation
- Git repository on `feat/foundation`

### Future architecture (not yet implemented)
- Six specialized agents (Profile, Career, Skill Gap, Learning, Interview,
  Evidence)
- Application-level orchestrator and LangGraph stateful workflows
- LLM provider abstraction (`LLMProvider` protocol)
- Supabase PostgreSQL, pgvector, Auth, and Storage
- Database schema and migrations
- Authentication and Row Level Security
- RAG / evidence pipeline
- Resume parsing
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

## Security boundaries
- Provider API keys and Supabase service role key: server-side only
- Frontend: only `NEXT_PUBLIC_*` variables, no secrets
- Authentication boundary: future Supabase Auth + RLS
- No secrets committed to git

## Agent execution trace concept (future)
Every agent run produces an inspectable execution trace stored in
`agent_runs` / `agent_events`. Traces make agent behavior auditable and are
not decorative animations.
