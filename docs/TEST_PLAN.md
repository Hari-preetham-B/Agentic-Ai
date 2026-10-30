# Test Plan — CareerTwin

## Future testing strategy

- Frontend unit tests
- Backend unit tests
- API tests
- Pydantic validation tests
- Agent workflow tests
- Evidence retrieval tests
- Claim classification tests
- Confidence-engine tests
- Integration tests
- End-to-end tests
- Security / authorization tests

## Tests implemented (Phase 2)

Backend (`apps/api/tests/`):

| Test | Covers |
|------|--------|
| `test_health.py` | backend starts, `/health` works, root meta |
| `test_profile.py` | profile create/retrieve/update/delete, child record CRUD, profile detail with children, validation structure, confirmation rejection when invalid, successful confirmation, profile status transitions |
| `test_resume.py` | TXT/PDF/DOCX extraction, empty file rejection, oversized file rejection, unsupported type rejection, filename sanitization, format detection by extension |
| `conftest.py` | in-memory SQLite (aiosqlite) session fixture so no real PostgreSQL is required |

Frontend (`apps/web/`):

| Check | Covers |
|-------|--------|
| `tsc --noEmit` | TypeScript strict type safety across onboarding flow and API client |
| `npm run lint` | ESLint (no explicit `any`, no unused vars) |
| `npm run build` | Next.js production build; all 17 routes prerender |
| Manual smoke test | onboarding start/profile/resume/review pages render; `/app/twin` renders |

## Validation commands

Backend:
```bash
cd apps/api
# .venv already created with dependencies
.venv\Scripts\python.exe -m pytest
```

Frontend:
```bash
cd/apps/web
npm run lint
npx tsc --noEmit
npm run build
```

## Tests implemented (Phase 5 — Evidence Intelligence)

Backend (`apps/api/tests/`):

| Test | Covers |
|------|--------|
| `test_evidence_models.py` | Evidence source/document/chunk/claim CRUD, claim-evidence links, constraints |
| `test_embedding_provider.py` | Fake embedding determinism, different inputs, batch, properties |
| `test_confidence_engine.py` | Deterministic scoring, SUPPORTED/CONTRADICTED/UNCERTAIN classification, reproducibility, source weights |
| `test_claim_extraction.py` | Deterministic extraction, context, empty text, short text |
| `test_claim_verification.py` | Claim verification pipeline, persistence |
| `test_evidence_agent.py` | Evidence Agent full run, empty input handling |
| `test_evidence_tools.py` | Tool registration, execution, validation |
| `test_evidence_api.py` | API endpoint availability |
| `test_evidence_ingestion.py` | Checksum dedup, chunking, metadata |
| `test_evidence_retriever.py` | Semantic search, min_similarity, get_chunk |

## Status
Phase 5 tests implemented. All backend tests passing (106 total). Frontend
typecheck, lint, and production build pass.
