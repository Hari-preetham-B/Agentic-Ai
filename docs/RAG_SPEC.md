# RAG / Evidence Specification — CareerTwin (Planned)

This document describes the planned evidence system. It is not implemented in
this stage.

## Future pipeline

```
Curated Sources
  → Ingestion
  → Chunking + Metadata
  → Embeddings
  → PostgreSQL + pgvector
  → Semantic + Metadata Retrieval
  → Evidence Agent
  → Claim/Evidence Comparison
  → Contradiction Detection
  → Confidence Engine
  → User-Facing Result
```

## Future evidence hierarchy (strongest → weakest)

1. user-confirmed information
2. uploaded documents
3. curated knowledge base
4. retrieved external information
5. LLM inference

## Future claim classes

| Class | Meaning |
|-------|---------|
| SUPPORTED | Claim is backed by evidence |
| INFERRED | Claim is reasoned from evidence but not directly stated |
| UNCERTAIN | Evidence is insufficient or conflicting |
| CONTRADICTED | Claim conflicts with evidence |

## Confidence rule

LLM self-reported confidence must NEVER be treated as system confidence.
Confidence is computed by the system's confidence engine using evidence
comparison and contradiction detection, not taken from an LLM's self-assessment.

## Status
Planned only. No RAG, pgvector, or evidence pipeline implemented yet.
