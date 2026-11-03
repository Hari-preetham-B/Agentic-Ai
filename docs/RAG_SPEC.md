# RAG / Evidence Specification — CareerTwin (Implemented — Phase 5)

This document describes the evidence intelligence system implemented in Phase 5
and validated in Phase 12 against the real Supabase PostgreSQL database and
Gemini embedding provider.

## Evidence pipeline

```
Curated Sources
  → Ingestion (EvidenceIngestionService)
  → Chunking + Metadata
  → Embeddings (EmbeddingProvider abstraction — Gemini embedding-2, 384 dims)
  → PostgreSQL + pgvector
  → Semantic + Metadata Retrieval (EvidenceRetriever)
  → Claim Extraction (ClaimExtractionService)
  → Claim/Evidence Comparison (ClaimVerificationService)
  → Contradiction Detection
  → Confidence Engine (deterministic)
  → User-Facing Result (Trust Center)
```

## Curated Evidence Corpus

The project maintains a small, deterministic, curated evidence corpus
(`apps/api/app/scripts/evidence_corpus.py`) containing authoritative sources
from U.S. government publications (O*NET, BLS) and official technology
documentation. The corpus covers all eight curated careers:

- Software Engineer
- Data Analyst
- Data Scientist
- Machine Learning Engineer
- AI Engineer
- Cybersecurity Analyst
- Cloud / DevOps Engineer
- Product Analyst

Each source includes occupational profiles and skill definitions. The corpus is
intentionally small — sufficient to exercise the full evidence pipeline without
web scraping or fabricated content.

## Embeddings

- **Provider**: Google Gemini (`google-genai` SDK)
- **Model**: `gemini-embedding-2`
- **Dimension**: 384 (fixed, validated)
- **Task type**: `RETRIEVAL_DOCUMENT` for document chunks, default for queries

Embeddings are generated through the `EmbeddingProvider` abstraction — never
directly from business logic. Both single-text and batch embedding are supported.

## Evidence Verification Claims

The claim verification pipeline (`ClaimVerificationService`) processes claims
through:

1. **Claim Extraction** (`ClaimExtractionService`): Extracts claims from text
   using the LLM provider with deterministic sentence-based fallback
2. **Evidence Retrieval** (`EvidenceRetriever`): pgvector cosine similarity
   search with top-K, minimum similarity threshold, and metadata filtering
3. **Claim/Evidence Comparison**: Deterministic Jaccard + retrieval similarity
   heuristic to classify each chunk as SUPPORTS / CONTRADICTS / CONTEXTUAL
4. **Confidence Calculation** (`ConfidenceEngine`): Deterministic scoring from
   source weights, document weights, similarity, agreement, contradiction,
   freshness, and directness
5. **Classification**: SUPPORTED / INFERRED / UNCERTAIN / CONTRADICTED

## Confidence rule

LLM self-reported confidence must NEVER be treated as system confidence.
Confidence is computed by the system's ConfidenceEngine using evidence
comparison and contradiction detection, not taken from an LLM's self-assessment.

### Confidence formula

Confidence is computed deterministically from observable signals — source
reliability, document type, retrieval similarity, agreement between evidence
chunks, contradiction strength, freshness, and directness. LLM self-reported
confidence is never used.

```
# Positive-support components (each in [0, 1]):
quality_score      = source_weight × document_weight × keyword_overlap
agreement_score    = mean(support_scores) × min(1.0, 0.5 + 0.1 × support_count)
directness_score   = 1.0 if directly_supported else 0.0
freshness_score    = 0.05

positive_support = (
    quality_score    * QUALITY_WEIGHT      # 0.20
    + agreement_score * AGREEMENT_WEIGHT   # 0.25
    + directness_score * DIRECTNESS_WEIGHT # 0.45
    + freshness_score * FRESHNESS_WEIGHT   # 0.10
)

contradiction_penalty = max(contradiction_scores) * CONTRADICTION_WEIGHT  # 0.35

score = clamp(positive_support - contradiction_penalty, 0.0, 1.0)
```

Source weights: USER_CONFIRMED=1.0, USER_DOCUMENT=0.9, CURATED_KNOWLEDGE=0.8,
RETRIEVED_EXTERNAL=0.6, LLM_INFERENCE=0.3.

Document type weights: OCCUPATIONAL_PROFILE=1.0, SKILL_DEFINITION=0.9,
INDUSTRY_REPORT=0.8, STANDARD_DOCUMENT=0.7, USER_RESUME=0.6, OTHER=0.5.

Formula weights: QUALITY_WEIGHT=0.20, AGREEMENT_WEIGHT=0.25,
DIRECTNESS_WEIGHT=0.45, FRESHNESS_WEIGHT=0.10 (sum to 1.0).
CONTRADICTION_WEIGHT=0.35.

### Classification thresholds

- CONTRADICTED: max contradiction > 0.50 OR score < 0.10 with contradiction
- SUPPORTED: score >= 0.70 and contradiction_penalty < 0.20
- INFERRED: score >= 0.40 and score < 0.70
- UNCERTAIN: score >= 0.10 and score < 0.40
- CONTRADICTED: score < 0.10 AND max_contradiction > 0.0

### Keyword overlap as primary signal

For short claims, pgvector cosine similarity can be unreliable because short
text embeddings don't align well with longer document embeddings. The system
uses keyword overlap (recall of claim keywords in evidence text) as the
primary quality signal:

keyword_overlap = |claim_keywords ∩ evidence_keywords| / |claim_keywords|

similarity = 0.6 * keyword_overlap + 0.4 * pgvector_similarity

## Deduplication

Document ingestion is idempotent by SHA-256 checksum of normalized content.
Source ingestion is idempotent by URL. Re-running ingestion does not create
duplicate documents, chunks, or sources.

## Validation

Validated against real Supabase PostgreSQL (pgvector) and Gemini embedding
provider:

- Single embedding: 384 dimensions, finite values, no NaN/Inf — PASS
- Batch embeddings: one vector per input, 384 dims each, ordering preserved — PASS
- Source creation, document creation, chunk creation — PASS
- Checksum deduplication, repeat ingestion idempotency — PASS
- Semantic search with pgvector cosine distance — PASS
- top-K behavior — PASS
- Minimum similarity threshold filtering — PASS
- Claim verification: supported, inferred, uncertain, contradicted — PASS
- Confidence engine: deterministic, thresholds, contradiction penalty — PASS
- EvidenceAgent: typed result, trace events — PASS

## Status

Implemented in Phase 5. Validated against real Supabase PostgreSQL and Gemini
embedding provider in Phase 12. pgvector-backed evidence storage, deterministic
confidence engine, and Trust Center UI are operational.