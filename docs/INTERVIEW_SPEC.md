# Interview Specification — CareerTwin (Phase 7)

## Overview

Phase 7 implements an adaptive interview intelligence system that provides
structured, stateful interview sessions with deterministic question selection,
difficulty progression, and skill performance tracking.

## Architecture

```
CareerTwin Profile
  → Target Career
  → Career Requirements
  → Interview Blueprint
  → Adaptive Question Selection (AdaptiveQuestionSelector)
  → Student Answer
  → Evaluation (InterviewEvaluationService)
  → Skill/Competency Update (InterviewSkillPerformanceService)
  → Next Question Selection
  → Interview Summary (InterviewCompletionService)
  → Improvement Recommendations
```

## Domain Model

### Tables

- `interview_sessions` — interview sessions with status, mode, difficulty
- `interview_questions` — question bank with type, difficulty, source
- `interview_question_skills` — question-to-skill mappings with relevance
- `interview_turns` — actual question/answer interactions
- `interview_evaluations` — structured evaluation output
- `interview_skill_results` — aggregated skill performance

### Session Statuses

CREATED → ACTIVE → PAUSED/COMPLETED/ABANDONED

### Question Types

TECHNICAL, CONCEPTUAL, SCENARIO, BEHAVIORAL, SYSTEM_DESIGN, PROBLEM_SOLVING

### Difficulty Levels

EASY, MEDIUM, HARD, EXPERT

## Question Bank

Curated baseline questions mapped to actual career skills. Idempotent seed
data. Questions map to known skills via `interview_question_skills`.

## Adaptive Question Selection

`AdaptiveQuestionSelector` uses deterministic scoring:

```
selection_score =
    0.35 * skill_need (gap × coverage need)
  + 0.25 * career_importance
  + 0.20 * coverage_need
  + 0.10 * difficulty_match
  + 0.05 * diversity_bonus
  - repetition_penalty
```

Ties broken by question ID (alphabetical).

## Adaptive Difficulty

`InterviewDifficultyEngine` uses a rolling window of 3 scores:
- recent average >= 0.80 → increase difficulty
- recent average <= 0.45 → decrease difficulty
- otherwise → maintain

## Session State Machine

Explicit transitions enforced by `InterviewSessionService`:
- CREATED → ACTIVE (start)
- ACTIVE → PAUSED (pause)
- PAUSED → ACTIVE (resume)
- ACTIVE/PAUSED → COMPLETED (complete)
- CREATED/ACTIVE/PAUSED → ABANDONED (abandon)

Invalid transitions are rejected with ValueError.

## Answer Evaluation

`InterviewEvaluationService` uses LLM with structured output:
- overall_score, correctness_score, depth_score, clarity_score, reasoning_score
- strengths, weaknesses, feedback
- All scores normalized to [0, 1]
- Malformed output returns controlled failure (zeros + error feedback)

## Skill Performance Aggregation

`InterviewSkillPerformanceService` calculates:
- questions_attempted
- average_score (running average)
- latest_score
- trend (IMPROVING/STABLE/DECLINING/INSUFFICIENT_DATA)
- performance_confidence (attempt_factor × consistency)

All deterministic — no LLM involvement.

## Interview Completion

`InterviewCompletionService` generates:
- overall score (mean of turn scores)
- skill performance summary
- strengths (skills with avg >= 0.70)
- weaknesses (skills with avg < 0.50)
- recommended skills (sorted weaknesses)
- difficulty progression

## Roadmap Integration

Interview performance provides a deterministic signal for roadmap regeneration.
Weak skills from interviews can influence roadmap regeneration but do NOT
overwrite confirmed profile skills. Interview-derived data is distinguishable
from user-confirmed data.

## Evidence Integration

Phase 5 evidence is used where factual claims require provenance (e.g.,
why a skill matters for a career). Interview evaluation is a performance
assessment, not an evidence verification task.

## Interview Agent

The Interview Agent orchestrates the full pipeline. LLM handles question
wording and answer evaluation. Deterministic services handle state, selection,
difficulty, scoring, completion, and progression.

## Tools

Registered tools:
- `create_interview_session` — create a session
- `get_interview_session` — get session state
- `get_next_interview_question` — get next question
- `submit_interview_answer` — submit an answer
- `evaluate_interview_answer` — evaluate an answer
- `get_interview_results` — get final results

## API Endpoints

- `POST /interviews` — create session
- `GET /interviews/{session_id}` — get session state
- `POST /interviews/{session_id}/start` — start
- `POST /interviews/{session_id}/pause` — pause
- `POST /interviews/{session_id}/resume` — resume
- `POST /interviews/{session_id}/complete` — complete
- `GET /interviews/{session_id}/results` — get results
- `POST /agent-runs` with `interview` capability

## Frontend

- `/app/interview` — interview workspace with setup, active, completed states
- `/app/careers` — updated with "Start interview →" link

## Status
Implemented in Phase 7.