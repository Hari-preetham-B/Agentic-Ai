# Database Schema — CareerTwin (Planned)

This document describes the planned major entities. It is a planned schema —
these tables do NOT exist yet and no migrations are implemented in this stage.

## Planned major entities

| Entity | Purpose |
|--------|---------|
| profiles | User's CareerTwin core profile state |
| education | Education history |
| skills | Evidenced and asserted skills |
| projects | Portfolio projects |
| experience | Work / role history |
| career_goals | Stated career objectives |
| career_paths | Plausible career directions |
| skill_gaps | Computed gaps vs target roles |
| learning_plans | Ordered learning plans |
| learning_items | Individual learning steps/milestones |
| interview_sessions | Interview preparation sessions |
| interview_answers | Answers given in sessions |
| evidence_sources | Documents/sources providing evidence |
| evidence_chunks | Chunks of evidence with embeddings |
| claims | Claims extracted from profile/sources |
| claim_evidence | Links between claims and evidence |
| agent_runs | Executed agent runs (trace root) |
| agent_events | Individual events within an agent run |

## Notes
- `pgvector` will support `evidence_chunks` embeddings for semantic retrieval.
- Supabase Auth will own user accounts; profiles link to auth users.
- PostgreSQL Row Level Security will enforce data ownership (future).
- No `claims` confidence is stored as LLM self-reported values; confidence is
  computed by the confidence engine.

## Status
Planned only. Do not pretend these tables exist.
