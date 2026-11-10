# What changed and why

## Crashes fixed (found by running the whole flow on real PostgreSQL)
- Roadmap read-back raised NameError (`r` vs `rr`) -> generated roadmaps could not load.
- Readiness crashed: `SkillDependencyService.get_missing_prerequisites` did not exist.
- Interview answers crashed: code wrote evaluation_status "COMPLETED"; DB constraint allows EVALUATED.
- Skills page sent a sentence as the career slug -> skill-gap analysis could never work.
- Agent runs looped to "Recursion limit reached" after any failed tool.
- Resume onboarding always failed: the extractor emitted invalid placeholder items. Replaced with a real parser
  (+ optional LLM structuring with validation and fallback). Skill levels are never guessed.
- Careers list returned empty skills so core-skill chips never rendered.
- Twin page spinner never ended for a user with no profile.
- Roadmap rows had no id (React key warning) and the page had no way to update progress: items now return their
  database id and each row has Not started / In progress / Done buttons.
- Removed the experimental `cacheComponents`/`partialPrefetching` flags from next.config.ts (they triggered a
  dev-only "Instant navigation" check; the app does not use them).

## Agents / traces
- Tool registry was process-global (concurrent requests shared DB sessions) -> now per-request.
- Agents now receive the real DB session and configured LLM provider (previously always fakes).
- Trace events: tool events persisted, strictly ordered, no duplicate AGENT_STARTED.

## Auth / config / setup
- Added HS256 (legacy JWT secret) verification next to JWKS; JWKS fetch no longer blocks the event loop;
  production refuses to start with the fake auth provider.
- `.env` is found from any working directory (repo root + apps/api); SUPABASE_SERVICE_ROLE_KEY accepted as alias;
  Next.js also reads the root `.env`.
- CORS origins configurable (CORS_ORIGINS) and include 127.0.0.1.
- Supabase transaction-pooler (6543) safe engine settings.
- New: `python -m app.scripts.setup_database`, `GET /health/diagnostics`, startup warnings.
- Interview `mode`/`difficulty` validated (422 instead of 500).
- Pages use the shared active profile instead of a one-time localStorage read.
- Missing dependencies declared (google-genai, aiosqlite, pytest-asyncio).

## Tests
- 188 pass (was 155 + 10 failing). New: test_regressions.py (each bug pinned and mutation-checked),
  test_profile_extractor.py, real-signature auth tests.
