# Project Specification — CareerTwin

## Project name
CareerTwin

## Project purpose
CareerTwin is an AI-powered career intelligence system for students. It
maintains an evolving structured representation of a student's professional
state — the CareerTwin — and uses it to power career path analysis, skill-gap
analysis, personalized learning roadmaps, adaptive interview preparation, and
evidence-aware information verification.

## Problem statement
Students lack a single, continuously updated model of their career state.
Existing tools treat resume review, job search, skill building, and interview
preparation as disconnected one-off interactions. CareerTwin instead maintains
a structured, evolving professional state and applies specialized AI agents
and deterministic services to it over time.

## Target users
- Students exploring career directions
- Students building and evidencing skills
- Students preparing for interviews
- Learners who want a longitudinal view of their professional growth

## Core capabilities
- Resume / manual profile onboarding (implemented: Phase 2)
- Structured CareerTwin profile with validation, persistence, and confirmation (implemented: Phase 2)
- Career path analysis
- Skill-gap analysis
- Personalized learning roadmaps
- Adaptive interview preparation
- Evidence-aware information verification
- Claim-level confidence classification
- Inspectable agent execution traces
- A premium dark technical/editorial UI

## Implementation status
Foundation (Phase 1) and Profile + Onboarding (Phase 2) are implemented. The profile is strongly typed,
validated, persisted in PostgreSQL, and reviewable/confirmable by the user. Resume upload (PDF/DOCX/TXT)
produces extracted text and a structured draft for review. No AI agents, LangGraph, RAG, or authentication
implemented yet.

## The CareerTwin concept
The CareerTwin represents:
- user information
- education
- skills
- projects
- experience
- interests
- career goals
- assessments
- learning progress
- interview performance
- agent-derived analysis
- evidence references

It is expected to evolve over time. The architecture avoids a collection of
disconnected one-off AI requests in favor of a persistent, inspectable state
model.

## Agentic AI requirement
CareerTwin must demonstrate genuine agentic AI architecture using
approximately six specialized agents:

1. Profile Agent
2. Career Agent
3. Skill Gap Agent
4. Learning Agent
5. Interview Agent
6. Evidence Agent

The project must NOT become a basic LLM wrapper — a simple application that
sends prompts to an LLM API and displays the response. Agents must be invoked
selectively, and deterministic application services must handle validation,
storage, calculations, skill-gap mathematics, retrieval, confidence
calculation, authorization, state persistence, and trace persistence.

## Evidence-aware requirement
The system separates supported information from inference. Every claim carries
a confidence classification and traceable evidence references. LLM self-reported
confidence must NEVER be treated as system confidence.

## Confidence requirement
Claims are classified as SUPPORTED, INFERRED, UNCERTAIN, or CONTRADICTED.
Confidence is computed by the system's confidence engine, not taken from an
LLM's self-assessment.

## Major scope boundaries
### In scope (eventually)
- All six agents and their selective invocation
- Deterministic services (validation, storage, calculations, retrieval,
  confidence, authorization, persistence, traces)
- Supabase (PostgreSQL + pgvector + Auth + Storage)
- Premium dark technical/editorial UI with Motion

### Out of scope (for now / permanently)
- A basic chatbot added purely for demonstration
- Fake agent traces or fake confidence values
- "Everything as an agent"
- Redis, Kafka, Celery, Kubernetes, or microservices
- 15+ agents

## Definition of done (foundation stage)
- Repository initialized with frontend, backend, shared package, and docs
- Next.js app runs on http://localhost:3000 with TypeScript, Tailwind, Motion
- FastAPI app runs on http://localhost:8000 with `/health`
- Pydantic Settings centralized configuration
- PostgreSQL/Supabase connected via SQLAlchemy async + asyncpg; Alembic initial migration
- Profile CRUD, child-record endpoints, validation, confirmation, resume extraction
- All nine source-of-truth documents exist and are internally consistent
- No real secrets committed; provider keys server-side only
- Basic test suite passes; frontend builds
- No AI agents, RAG, authentication, or database schema implemented
