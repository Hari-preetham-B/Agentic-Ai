# Database Schema — CareerTwin

## Status
Implemented in Phase 2 (Profile + Onboarding). The following six core tables exist
in PostgreSQL via SQLAlchemy + Alembic. All other tables (career_paths, skill_gaps,
learning_plans, interview_sessions, evidence_sources, claims, agent_runs, ...) are
planned for later phases and do NOT exist yet.

## Implemented tables

### profiles
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | primary key |
| user_id | UUID | nullable, indexed; bound to Supabase Auth identity in a later phase |
| full_name | TEXT | nullable |
| headline | TEXT | nullable |
| email | TEXT | nullable |
| phone | TEXT | nullable |
| location | TEXT | nullable |
| summary | TEXT | nullable |
| profile_status | TEXT | NOT NULL, default `DRAFT`. Values: DRAFT / REVIEW / CONFIRMED |
| created_at | TIMESTAMPTZ | NOT NULL, default now() |
| updated_at | TIMESTAMPTZ | NOT NULL, default now() |

### education
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | primary key |
| profile_id | UUID | FK → profiles.id, ON DELETE CASCADE |
| institution | TEXT | NOT NULL |
| degree | TEXT | nullable |
| field_of_study | TEXT | nullable |
| start_date | DATE | nullable |
| end_date | DATE | nullable |
| description | TEXT | nullable |
| created_at | TIMESTAMPTZ | NOT NULL |

### skills
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | primary key |
| profile_id | UUID | FK → profiles.id, ON DELETE CASCADE |
| name | TEXT | NOT NULL |
| category | TEXT | nullable |
| proficiency | TEXT | CHECK: BEGINNER/INTERMEDIATE/ADVANCED/EXPERT or NULL |
| years_experience | NUMERIC(3,1) | nullable |
| source | TEXT | NOT NULL, default USER_CONFIRMED. CHECK: USER_CONFIRMED/DOCUMENT_EXTRACTED/SYSTEM_INFERRED |
| created_at | TIMESTAMPTZ | NOT NULL |

### projects
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | primary key |
| profile_id | UUID | FK → profiles.id, ON DELETE CASCADE |
| name | TEXT | NOT NULL |
| description | TEXT | nullable |
| technologies | JSON | nullable |
| role | TEXT | nullable |
| outcomes | TEXT | nullable |
| start_date | DATE | nullable |
| end_date | DATE | nullable |
| source | TEXT | NOT NULL, default USER_CONFIRMED. CHECK: USER_CONFIRMED/DOCUMENT_EXTRACTED/SYSTEM_INFERRED |
| created_at | TIMESTAMPTZ | NOT NULL |

### experience
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | primary key |
| profile_id | UUID | FK → profiles.id, ON DELETE CASCADE |
| organization | TEXT | NOT NULL |
| role | TEXT | NOT NULL |
| description | TEXT | nullable |
| achievements | TEXT | nullable |
| start_date | DATE | nullable |
| end_date | DATE | nullable |
| is_current | BOOLEAN | NOT NULL, default false |
| source | TEXT | NOT NULL, default USER_CONFIRMED. CHECK: USER_CONFIRMED/DOCUMENT_EXTRACTED/SYSTEM_INFERRED |
| created_at | TIMESTAMPTZ | NOT NULL |

### career_goals
| Column | Type | Notes |
|--------|------|-------|
| id | UUID | primary key |
| profile_id | UUID | FK → profiles.id, ON DELETE CASCADE |
| target_role | TEXT | NOT NULL |
| target_industry | TEXT | nullable |
| target_domain | TEXT | nullable |
| goal_description | TEXT | nullable |
| priority | INTEGER | NOT NULL, default 1 |
| created_at | TIMESTAMPTZ | NOT NULL |

## Design
- All child records reference `profiles.id` via foreign keys with cascading deletes.
- UUID primary keys throughout.
- Timestamps consistently applied.
- Database constraints (CHECK on `proficiency` and `source`) complement Pydantic
  application-level validation.
- Migration: `alembic/versions/0001_initial_schema.py` (initial schema).

## Not yet implemented
career_paths, skill_gaps, learning_plans, learning_items, interview_sessions,
interview_answers, evidence_sources, evidence_chunks, claims, claim_evidence,
agent_runs, agent_events.
