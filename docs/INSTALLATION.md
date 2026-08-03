# Installation Guide

Complete local setup for the Enterprise AI Personal Agent.

## Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.12+ | Backend |
| Node.js | 20+ | Frontend (Next.js 15 requires Node 18.18+, 20 LTS recommended) |
| npm | 10+ | Ships with Node 20 |
| A Supabase project | — | Free tier is fine to start |
| A Google Cloud project | — | For Gemini, Gmail/Calendar/Drive, Speech/TTS — see [GOOGLE_CLOUD_SETUP.md](GOOGLE_CLOUD_SETUP.md) |

## 1. Clone and Inspect

```bash
git clone <your-repo-url> enterprise-ai-agent
cd enterprise-ai-agent
```

The project has two independent apps: `backend/` (FastAPI) and `frontend/`
(Next.js). They run as separate processes locally and deploy to separate
platforms (Render and Vercel respectively).

## 2. Supabase Setup

1. Create a project at [supabase.com](https://supabase.com).
2. Note your **Project URL**, **anon key**, and **service_role key**
   (Settings → API).
3. In the SQL Editor, run these files **in order**:
   1. `backend/app/database/schema.sql`
   2. `backend/app/database/schema_phase2_agent.sql`
   3. `backend/app/database/schema_phase5_enterprise.sql`
4. Create a Storage bucket named `user-uploads` (Storage → New Bucket,
   **private**) — used by File Intelligence and Vision AI.

## 3. Google Cloud Setup

Follow [GOOGLE_CLOUD_SETUP.md](GOOGLE_CLOUD_SETUP.md) in full. You'll come
away with:
- A **Gemini API key**
- An **OAuth 2.0 Client ID/Secret** (Gmail/Calendar/Drive)
- A **service account JSON key** (Speech-to-Text/Text-to-Speech)

## 4. Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` and fill in at minimum:

```bash
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_ANON_KEY=...
GEMINI_API_KEY=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
TOKEN_ENCRYPTION_KEY=...          # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
OAUTH_STATE_SECRET=...            # python -c "import secrets; print(secrets.token_urlsafe(48))"
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account-key.json
```

Optional but recommended for full functionality: `WEATHER_API_KEY` is not
required (weather uses the free Open-Meteo API), but `WEB_SEARCH_API_KEY`
(Brave Search) is required for the web_search tool/Research Agent.

Run it:

```bash
uvicorn app.main:app --reload --port 8000
```

Verify: open `http://localhost:8000/docs` (interactive Swagger UI) and
`http://localhost:8000/api/v1/health`.

## 5. Frontend Setup

```bash
cd frontend
npm install
cp .env.local.example .env.local
```

Edit `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=...
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

(Firebase values aren't required to be real yet — the sign-in flow that
consumes them lands in a later phase — but the frontend build expects the
env keys to be present.)

Run it:

```bash
npm run dev
```

Open `http://localhost:3000`.

## 6. Identify Yourself as a User (Interim, Pre-Auth)

Since Firebase sign-in hasn't landed yet, authenticated backend requests
need an `X-User-Id` header equal to a row's `id` in the Supabase `users`
table. For local testing, insert one manually:

```sql
insert into public.users (firebase_uid, email, display_name)
values ('local-dev-uid', 'you@example.com', 'Local Dev')
returning id;
```

Use the returned `id` as `X-User-Id` in requests (Swagger UI's "Authorize"
won't have a slot for this — add it manually per-request via the "Try it
out" headers, or use `curl`/Postman/Insomnia).

## 7. Smoke Test

```bash
curl http://localhost:8000/api/v1/health

curl -X POST http://localhost:8000/api/v1/agent/chat \
  -H "Content-Type: application/json" \
  -H "X-User-Id: <the uuid from step 6>" \
  -d '{"message": "What time is it in Tokyo?"}'
```

You should get a JSON response with `answer`, `run_id`, `agent_name`
(likely `"assistant_agent"` or `"research_agent"`), and `status: "completed"`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `gemini_not_configured` error | Missing/invalid `GEMINI_API_KEY` |
| `supabase_not_configured` error | Missing `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` |
| `401` on every request | Missing `X-User-Id` header |
| `404 profile not found` on `/users/me` | No `users` row exists yet for that ID (see step 6) |
| Google tool calls fail with `google_reauth_required` | Complete `/google/oauth/authorize` → consent flow first |
| Voice endpoints fail | `GOOGLE_APPLICATION_CREDENTIALS` not set or points to an invalid/unauthorized service account key |
| File/image upload fails with a storage error | The `user-uploads` bucket doesn't exist yet in Supabase Storage |
