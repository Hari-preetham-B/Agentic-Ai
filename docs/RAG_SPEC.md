# RAG / Evidence Specification — CareerTwin (Implemented — Phase 5)

This document describes the evidence intelligence system implemented in Phase 5.

## Evidence pipeline

```
Curated Sources
  → Ingestion (EvidenceIngestionService)
  → Chunking + Metadata
  → Embeddings (EmbeddingProvider abstraction)
  → PostgreSQL + pgvector
  → Semantic + Metadata Retrieval (EvidenceRetriever)
  → Claim Extraction (ClaimExtractionService)
  → Claim/Evidence Comparison (ClaimVerificationService)
  → Contradiction Detection
  → Confidence Engine (deterministic)
  → User-Facing Result (Trust Center)
```

## Evidence hierarchy (strongest → weakest)

1. USER_CONFIRMED
2. USER_DOCUMENT
3. CURATED_KNOWLEDGE
4. RETRIEVED_EXTERNAL
5. LLM_INFERENCE

## Claim classes

| Class | Meaning |
|-------|---------|
| SUPPORTED | Claim is backed by strong direct evidence with no material contradiction |
| INFERRED | Claim is reasoned from evidence but not directly stated |
| UNCERTAIN | Evidence is insufficient or conflicting |
| CONTRADICTED | Claim conflicts with reliable evidence |

## Confidence rule

LLM self-reported confidence must NEVER be treated as system confidence.
Confidence is computed by the system's ConfidenceEngine using evidence
comparison and contradiction detection, not taken from an LLM's self-assessment.

### Confidence formula

```
base = mean(source_weight × document_weight × similarity)
agreement = mean(support_scores) × min(1.0, 0.5 + 0.1 × support_count)
contradiction_penalty = max(contradiction_scores) × 0.25
freshness_bonus = 0.05 × 0.10
directness_bonus = 0.05 if directly_supported else 0.0

raw_score = base × 0.30 + agreement × 0.30 - contradiction_penalty + freshness_bonus + directness_bonus
score = clamp(raw_score, 0.0, 1.0)
```

Source weights: USER_CONFIRMED=1.0, USER_DOCUMENT=0.9, CURATED_KNOWLEDGE=0.8,
RETRIEVED_EXTERNAL=0.6, LLM_INFERENCE=0.3.

### Classification thresholds

- CONTRADICTED: max contradiction > 0.50, OR score < 0.10 with contradiction
- SUPPORTED: score >= 0.70 and contradiction penalty < 0.20
- INFERRED: score >= 0.40
- UNCERTAIN: score >= 0.10
- CONTRADICTED: score < 0.10 (fallback)

## Status
Implemented in Phase 5. pgvector-backed evidence storage, deterministic
confidence engine, and Trust Center UI are operational.