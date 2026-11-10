# CareerTwin patch — how to apply

This archive contains ONLY the files that changed. Folder paths match your project root
(the folder containing `apps/`, `README.md`, `.env.example`).

## 1. Apply
1. Close the running API and web servers. Back up your project (or commit it to git first).
2. Unzip this archive and **copy its contents over your project folder**, accepting overwrite.
   Your real `.env` / `.env.local` files are NOT in the archive and are not touched.
   (Windows: drag the `apps`, `README.md` and `.env.example` items into your project folder;
   macOS/Linux: `cp -R careertwin-patch/. /path/to/your/project/`)

## 2. Configure (one file)
Create `.env` in the project root from `.env.example` (see comments inside). Minimum:
`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_URL`,
`SUPABASE_SECRET_KEY`, `DATABASE_URL` (Session-pooler string, scheme `postgresql+asyncpg://`),
and optionally `LLM_API_KEY`. If your old settings live in `apps/api/.env` or `apps/web/.env.local`
they still work and take priority.

## 3. Backend
```
cd apps/api
pip install -e ".[dev]"                  # new deps: google-genai, aiosqlite, pytest-asyncio
python -m app.scripts.setup_database     # migrations + seeds, safe to re-run, never drops data
uvicorn app.main:app --reload --port 8000
```
Open http://localhost:8000/health/diagnostics — it lists anything still misconfigured.

## 4. Frontend
```
cd apps/web
npm install
npm run dev
```
Open http://localhost:3000.

## 5. Verify
```
cd apps/api && python -m pytest          # expect: 188 passed, 32 skipped
cd apps/web && npx tsc --noEmit && npx eslint
```
