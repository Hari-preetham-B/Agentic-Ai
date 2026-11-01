# External Providers — CareerTwin

This document describes the external services required to run CareerTwin
in production. No real credentials are included.

## Supabase

### Required credentials

1. **Project URL** (`SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_URL`)
   - Where to obtain: Supabase Dashboard → Settings → API → Project URL
   - Secret: No (public, safe for browser)
   - Used by: Frontend (browser) and Backend (server)
   - Format: `https://<project-ref>.supabase.co`

2. **Publishable/Anon Key** (`NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`)
   - Where to obtain: Supabase Dashboard → Settings → API → anon/public key
   - Secret: No (public, safe for browser)
   - Used by: Frontend (browser) only
   - Format: `eyJ...` (JWT)

3. **Service Role Key** (`SUPABASE_SERVICE_ROLE_KEY`)
   - Where to obtain: Supabase Dashboard → Settings → API → service_role key
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only
   - Format: `eyJ...` (JWT)

4. **JWT Secret** (`SUPABASE_JWT_SECRET`)
   - Where to obtain: Supabase Dashboard → Settings → API → JWT Secret
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only
   - Format: `your-jwt-secret`

5. **PostgreSQL Connection URL** (`DATABASE_URL`)
   - Where to obtain: Supabase Dashboard → Settings → Database → Connection string
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only
   - Format: `postgresql+asyncpg://postgres:<password>@<host>:5432/postgres`

### RLS Compatibility

Supabase uses PostgreSQL with Row Level Security. The migration
`0006_row_level_security.py` enables RLS on user-owned tables. When
connecting to Supabase, ensure RLS policies are applied.

## LLM

### Required credentials

1. **Provider** (`LLM_PROVIDER`)
   - Options: `fake` (development), `openai`, `anthropic`, `gemini`, etc.
   - Secret: No
   - Used by: Backend (server) only

2. **Model** (`LLM_MODEL`)
   - Example: `gpt-4`, `claude-3-sonnet`, `gemini-pro`
   - Secret: No
   - Used by: Backend (server) only

3. **API Key** (`LLM_API_KEY`)
   - Where to obtain: Provider's dashboard
   - Secret: Yes (NEVER expose to browser)
   - Used by: Backend (server) only

### Architecture

Agents depend on the `LLMProvider` protocol, not vendor SDKs. The provider
is selected via configuration and injected at runtime. `FakeLLMProvider`
is used for tests and local development.

## Embeddings

### Required credentials

1. **Provider** (`EMBEDDING_PROVIDER`)
   - Options: `fake` (development), `openai`, `cohere`, etc.
   - Secret: No
   - Used by: Backend (server) only

2. **Model** (`EMBEDDING_MODEL`)
   - Example: `text-embedding-3-small`, `embed-english-v3.0`
   - Secret: No
   - Used by: Backend (server) only

3. **API Key** (`EMBEDDING_API_KEY`)
   - Where to obtain: Provider's dashboard
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
LLM_PROVIDER=fake
EMBEDDING_PROVIDER=fake
EMBEDDING_DIMENSION=384
```

### Tests
Tests use `FakeAuthProvider`, `FakeLLMProvider`, and `FakeEmbeddingProvider`.
No external credentials are required.<|end|>