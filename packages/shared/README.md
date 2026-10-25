# CareerTwin Shared Package

This package holds contracts and types that genuinely need to be shared between
the Next.js frontend (`apps/web`) and the FastAPI backend (`apps/api`).

## What belongs here

- Shared type definitions that both sides must agree on (e.g. enumeration
  values, status codes, lightweight request/response shapes) — expressed in a
  way that is easy to mirror in both TypeScript and Python.
- Minimal, stable constants (e.g. route names, claim confidence classes) that
  both applications reference.

## What does NOT belong here

- Business logic, validation rules, or calculations. Those live in the
  backend `services/` layer.
- Agent orchestration, LangGraph workflows, or LLM provider code.
- Database models or Supabase client code.
- Frontend UI components.

## Python ↔ TypeScript

Do not force Python and TypeScript to share code if doing so creates
unnecessary complexity. The two applications communicate over HTTP/JSON; the
shared package is for the small surface that truly needs to stay in sync, not
for duplicating implementations.

Currently this package is intentionally empty. It is established now so the
contract boundary exists before Phase 2 (profile and onboarding) begins.
