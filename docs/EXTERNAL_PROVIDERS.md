# External Providers — CareerTwin

This document describes the external services required to run CareerTwin
in production. No real credentials are included.

## Current Development Provider: Google Gemini

CareerTwin uses Google Gemini as the current development LLM and embedding
provider.

### LLM
- Provider: `gemini`
- Model: `gemini-3.8-flash`
- API key environment variable: `LLM_API_KEY`
- Backend-only (never exposed to frontend)

### Embeddings
- Provider: `gemini`
- Model: `gemini-embedding-2`
- API key environment variable: `EMBEDDING_API_KEY`
- Output dimension: `384`
- Environment variable: `EMBEDDING_DIMENSION=384`
- Backend-only (never exposed to frontend)

### Important Notes
- The application remains provider-independent. Gemini is the current
  development provider, but the architecture supports swapping providers
  without changing agent code.
- Automated tests use `FakeLLMProvider` and `FakeEmbeddingProvider`.
  No real API calls are made during normal test runs.
- Changing embedding models requires re-embedding existing evidence vectors
  because embedding spaces are not interchangeable.
- The pgvector column uses `Vector(384)`. The production embedding model
  must produce exactly 384 dimensions unless the schema is intentionally
  changed via migration.

## Supabase

### Required credentials

1. **Project URL** (`SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`)
   - Where to obtain: Supabase Dashboard → Settings → API → Project URL
   - Secret: No (public, safe for browser)
   - Used by: Frontend (browser) and Backend (server)

2. **Publishable/Anon Key** (`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` / `SUPABASE_PUBLISHABLE_KEY`)
   - Where to obtain: Supabase Dashboard → Settings → API → anon/public key
   - Secret: No (public, safe for browser)
   - Used by: Frontend (browser) and Backend (server)

3. **Secret Key** (`SUPABASE_SECRET_KEY`)
   - Where to obtain: Supabase Dashboard → Settings → API → service_role key
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only

4. **JWT Secret** (`SUPABASE_JWT_SECRET`)
   - Where to obtain: Supabase Dashboard → Settings → API → JWT Secret
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only

5. **PostgreSQL Connection URL** (`DATABASE_URL`)
   - Where to obtain: Supabase Dashboard → Settings → Database → Connection string
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only

### RLS Compatibility

Supabase uses PostgreSQL with Row Level Security. The migration
`0006_row_level_security` enables RLS on user-owned tables.

## LLM

### Required credentials

1. **Provider** (`LLM_PROVIDER`)
   - Current: `gemini`
   - Secret: No
   - Used by: Backend (server) only

2. **Model** (`LLM_MODEL`)
   - Current: `gemini-3.8-flash`
   - Secret: No
   - Used by: Backend (server) only

3. **API Key** (`LLM_API_KEY`)
   - Where to obtain: Google AI Studio → API Keys
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only

### Architecture

Agents depend on the `LLMProvider` protocol, not vendor SDKs. The provider
is selected via configuration and injected at runtime. `FakeLLMProvider`
is used for tests and local development.

## Embeddings

### Required credentials

1. **Provider** (`EMBEDDING_PROVIDER`)
   - Current: `gemini`
   - Secret: No
   - Used by: Backend (server) only

2. **Model** (`EMBEDDING_MODEL`)
   - Current: `gemini-embedding-2`
   - Secret: No
   - Used by: Backend (server) only

3. **API Key** (`EMBEDDING_API_KEY`)
   - Where to obtain: Google AI Studio → API Keys
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only

4. **Dimension** (`EMBEDDING_DIMENSION`)
   - Current value: `384`
   - The production embedding model MUST produce exactly 384 dimensions
     unless the schema is intentionally changed via migration.
   - Secret: No

### Architecture

Embeddings are abstracted behind `EmbeddingProvider`. The pgvector column
uses `Vector(384)`. `FakeEmbeddingProvider` produces deterministic
384-dimensional vectors for tests.

## Real Provider Smoke Test

To manually test the real Gemini providers:

```bash
cd apps/api
python tests/test_gemini_smoke.py
```

Or with pytest (not run by default):

```bash
cd apps/api
pytest tests/test_gemini_smoke.py -v -s
```

The smoke test requires:
- `LLM_PROVIDER=gemini` and `LLM_API_KEY` set in `.env`
- `EMBEDDING_PROVIDER=gemini` and `EMBEDDING_API_KEY` set in `.env`

It will:
1. Send a minimal prompt to Gemini
2. Perform one structured-output request
3. Generate one embedding
4. Verify the embedding has exactly 384 dimensions

The smoke test never prints the API key or sensitive request headers.

## Local Development

### Frontend (.env.local)
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (.env)
```
ENVIRONMENT=development
DATABASE_URL=sqlite+aiosqlite:///./test.db
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.8-flash
LLM_API_KEY=<your-key>
EMBEDDING_PROVIDER=gemini
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_API_KEY=<your-key>
EMBEDDING_DIMENSION=384
```

### Tests
Tests use `FakeAuthProvider`, `FakeLLMProvider`, and `FakeEmbeddingProvider`.
No external credentials are required for the normal test suite.
The smoke test (`test_gemini_smoke.py`) is excluded from normal pytest runs.