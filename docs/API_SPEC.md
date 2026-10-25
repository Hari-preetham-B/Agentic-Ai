# API Specification — CareerTwin (Planned)

This document describes the future API surface at a high level. Only
`GET /health` is implemented in this stage.

## Future API groups

| Group | Purpose | Status |
|-------|---------|--------|
| `/auth` | Authentication (Supabase Auth + FastAPI validation) | Not implemented |
| `/profile` | CareerTwin profile CRUD | Not implemented |
| `/careertwin` | Evolving professional state | Not implemented |
| `/careers` | Career path analysis | Not implemented |
| `/skills` | Skill intelligence and gaps | Not implemented |
| `/roadmap` | Learning roadmaps | Not implemented |
| `/interview` | Interview lab sessions | Not implemented |
| `/evidence` | Evidence sources and claims | Not implemented |
| `/agent-runs` | Agent execution traces | Not implemented |

## Implemented in this stage

- `GET /health` — structured health check:
  ```json
  {
    "status": "ok",
    "service": "careertwin-api",
    "environment": "development"
  }
  ```
- `GET /docs` — FastAPI interactive documentation
- `GET /redoc` — ReDoc documentation

## Design principles
- Provider API keys and Supabase service role key are server-side only.
- Frontend calls the backend over HTTP; frontend never holds secrets.
- Authentication and authorization enforced by FastAPI (future Supabase Auth +
  RLS).
