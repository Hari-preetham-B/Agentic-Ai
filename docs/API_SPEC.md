# API Specification — CareerTwin

## Data flow
```
Browser
  ↓
Next.js (http://localhost:3000)
  ↓
FastAPI (http://localhost:8000)
  ↓
SQLAlchemy async + asyncpg → PostgreSQL (Supabase)
```

## Implemented endpoints (Phase 2 — Profile + Onboarding)

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/health` | GET | Structured health check | Implemented (Phase 1) |
| `/profiles` | POST | Create a new profile draft | Implemented |
| `/profiles/{profile_id}` | GET | Get a profile by ID | Implemented |
| `/profiles/{profile_id}/detail` | GET | Get a profile with all child records | Implemented |
| `/profiles/{profile_id}` | PUT | Update a profile | Implemented |
| `/profiles/{profile_id}` | DELETE | Delete a profile and all child records | Implemented |
| `/profiles/{profile_id}/validate` | POST | Validate without confirming | Implemented |
| `/profiles/{profile_id}/confirm` | POST | Confirm a profile (status → CONFIRMED) | Implemented |
| `/profiles/{profile_id}/education` | POST | Add education record | Implemented |
| `/profiles/{profile_id}/education` | GET | List education records | Implemented |
| `/profiles/{profile_id}/education/{child_id}` | PUT | Update education record | Implemented |
| `/profiles/{profile_id}/education/{child_id}` | DELETE | Delete education record | Implemented |
| `/profiles/{profile_id}/skills` | POST | Add skill record | Implemented |
| `/profiles/{profile_id}/skills` | GET | List skill records | Implemented |
| `/profiles/{profile_id}/skills/{child_id}` | PUT | Update skill record | Implemented |
| `/profiles/{profile_id}/skills/{child_id}` | DELETE | Delete skill record | Implemented |
| `/profiles/{profile_id}/projects` | POST | Add project record | Implemented |
| `/profiles/{profile_id}/projects` | GET | List project records | Implemented |
| `/profiles/{profile_id}/projects/{child_id}` | PUT | Update project record | Implemented |
| `/profiles/{profile_id}/projects/{child_id}` | DELETE | Delete project record | Implemented |
| `/profiles/{profile_id}/experience` | POST | Add experience record | Implemented |
| `/profiles/{profile_id}/experience` | GET | List experience records | Implemented |
| `/profiles/{profile_id}/experience/{child_id}` | PUT | Update experience record | Implemented |
| `/profiles/{profile_id}/experience/{child_id}` | DELETE | Delete experience record | Implemented |
| `/profiles/{profile_id}/career-goals` | POST | Add career goal | Implemented |
| `/profiles/{profile_id}/career-goals` | GET | List career goals | Implemented |
| `/profiles/{profile_id}/career-goals/{child_id}` | PUT | Update career goal | Implemented |
| `/profiles/{profile_id}/career-goals/{child_id}` | DELETE | Delete career goal | Implemented |
| `/profiles/extract-resume` | POST | Upload resume, return extracted text | Implemented |
| `/profiles/extract-resume/draft` | POST | Upload resume, return structured ProfileDraft | Implemented |

## Implemented endpoints (Phase 5 — Evidence Intelligence)

| Endpoint | Method | Description | Status |
|----------|--------|-------------|--------|
| `/evidence/search` | POST | Search evidence chunks by semantic similarity | Implemented |
| `/claims/verify` | POST | Verify a claim against stored evidence | Implemented |
| `/claims/{claim_id}` | GET | Get a verified claim by ID | Implemented |
| `/claims/{claim_id}/evidence` | GET | Get evidence linked to a claim | Implemented |
| `/evidence/ingest` | POST | Ingest an evidence document (idempotent) | Implemented |

## Planned (future) endpoints
| Group | Purpose | Status |
|-------|---------|--------|
| `/auth` | Authentication (Supabase Auth + FastAPI validation) | Not implemented |
| `/careers` | Career path analysis | Implemented (Phase 4) |
| `/skills` | Skill intelligence and gaps | Implemented (Phase 4) |
| `/roadmap` | Learning roadmaps | Not implemented |
| `/interview` | Interview lab sessions | Not implemented |
| `/evidence` | Evidence search and ingestion | Implemented (Phase 5) |
| `/claims` | Claim verification and retrieval | Implemented (Phase 5) |
| `/agent-runs` | Agent execution traces | Implemented (Phase 3) |

## Health check (implemented)
```json
{
  "status": "ok",
  "service": "careertwin-api",
  "environment": "development"
}
```

## Design principles
- Provider API keys and Supabase service role key are server-side only.
- Frontend calls the backend over HTTP; frontend never holds secrets.
- Every API operation requires a profile ID; ownership checks are possible
  once Supabase Auth is implemented.
- Structured error responses; no raw stack traces to users.
