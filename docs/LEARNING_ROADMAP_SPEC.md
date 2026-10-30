# Learning Roadmap Specification — CareerTwin (Phase 6)

## Overview

Phase 6 implements a dependency-aware career roadmap system that transforms
skill gaps into a sequenced, prioritized learning plan.

## Architecture

```
CareerTwin Profile
  → Target Career
  → Deterministic Skill Gap (SkillMatchingEngine)
  → Skill Dependencies (SkillDependencyService)
  → Learning Resource Catalog
  → Resource Matching (LearningResourceMatcher)
  → Priority Engine (RoadmapPriorityEngine)
  → Sequencing Engine (RoadmapSequenceEngine)
  → Personalized Roadmap (LearningRoadmapService)
  → Evidence-Aware Recommendations
```

## Data Model

### Tables

- `learning_resources` — curated learning resources (courses, tutorials, docs, etc.)
- `skill_dependencies` — prerequisite relationships between skills
- `learning_resource_skills` — many-to-many mapping (resource → skill)
- `roadmaps` — personalized roadmaps per profile/career
- `roadmap_items` — individual skills in a roadmap
- `roadmap_resources` — resource mappings per roadmap item

### Key Constraints

- Unique constraint on (skill_id, prerequisite_skill_id) in skill_dependencies
- No self-dependencies (skill_id != prerequisite_skill_id)
- Foreign keys with CASCADE delete on all relationships

## Dependency Graph

Skills are connected via prerequisite relationships forming a DAG.
Cycle detection uses DFS. Topological sort uses Kahn's algorithm with
deterministic alphabetical tie-breaking.

### Prerequisite Closure

For a given skill, the full set of transitive prerequisites is computed
via DFS traversal of the dependency graph.

## Learning Resource Catalog

Small curated dataset of free resources from:
- Official documentation (Python, PostgreSQL, Docker, Kubernetes)
- freeCodeCamp
- MDN
- Microsoft Learn
- Google Cloud documentation

Idempotent seed command: `scripts/seed_learning_resources.py`

## Resource Matching

`LearningResourceMatcher` ranks resources using:
- Skill relevance (relevance_score from mapping)
- Coverage (whether resource covers the skill)
- Difficulty fit (resource difficulty vs current proficiency)
- Resource type weight (PROJECT > COURSE > TUTORIAL > DOCUMENTATION > BOOK > PRACTICE > VIDEO)
- Effort factor (lower effort preferred)

Formula: `0.35*relevance + 0.20*coverage + 0.20*difficulty_fit + 0.15*type_weight + 0.10*effort_factor`

## Priority Engine

`RoadmapPriorityEngine` calculates P0/P1/P2 using:
- Gap severity (missing=1.0, partial=0.5)
- Career importance (CORE=1.0, IMPORTANT=0.7, SUPPORTING=0.4)
- Current proficiency (BEGINNER=1.0, INTERMEDIATE=0.6, ADVANCED=0.3, EXPERT=0.1)
- Dependency centrality (downstream skills unlocked)
- Effort factor

Thresholds: P0 >= 0.70, P1 >= 0.40, P2 < 0.40

## Sequencing

`RoadmapSequenceEngine` uses topological sort (Kahn's algorithm) to ensure
prerequisites appear before dependents. Ties broken by priority then alphabetically.

## Roadmap Regeneration

When profile changes, the roadmap can be regenerated. Old roadmap is deleted
(cascade) and a new one is generated with updated skill gaps and sequencing.

## Learning Agent

The Learning Agent orchestrates the full pipeline:
Profile/Career → Skill Gap → Dependencies → Priority → Resource Matching →
Roadmap Generation → Evidence-aware explanation

LLM may generate rationale/explanations but does NOT calculate gaps,
determine prerequisites, rank resources, or assign priorities.

## Tools

Registered tools:
- `get_learning_resources` — retrieve resources by skill/type
- `get_skill_dependencies` — get prerequisite graph for a skill
- `calculate_learning_priority` — deterministic priority calculation
- `generate_learning_roadmap` — generate a full roadmap
- `get_roadmap` — retrieve a roadmap by ID

## API Endpoints

- `GET /learning/resources` — list learning resources
- `GET /learning/dependencies/{skill_name}` — get skill dependencies
- `POST /learning/roadmaps` — generate a learning roadmap
- `GET /learning/roadmaps/{roadmap_id}` — get a roadmap
- `POST /learning/roadmaps/{roadmap_id}/regenerate` — regenerate a roadmap
- `POST /agent-runs` with `learning_roadmap` capability

## Frontend

- `/app/roadmap` — vertical learning path with numbered stages, priority badges,
  skill nodes, prerequisite indicators, estimated effort, resource references
- `/app/careers` — updated with "Build roadmap →" link

## Evidence Integration

Roadmap items reference career requirement evidence and skill-gap calculations
for provenance. No fabricated evidence.

## Status
Implemented in Phase 6.