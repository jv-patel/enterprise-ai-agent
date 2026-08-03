# Deployment Guide

The backend deploys to **Render**, the frontend to **Vercel**. They're
independent deployments that talk to each other over HTTPS.

## Backend → Render

### Option A: Blueprint (recommended)

The repo includes `render.yaml` at the project root, defining the service,
build/start commands, and health check.

1. Push the repo to GitHub/GitLab.
2. In the Render Dashboard: **New → Blueprint**, select the repo.
3. Render reads `render.yaml` and provisions the `enterprise-ai-agent-backend`
   web service (Python runtime, `rootDir: backend`).
4. Fill in every environment variable marked `sync: false` in `render.yaml`
   (Render prompts for these during Blueprint setup) — see the full list and
   descriptions in [INSTALLATION.md](INSTALLATION.md) and
   `backend/.env.example`.
5. For `GOOGLE_APPLICATION_CREDENTIALS`: upload your service account JSON as
   a **Secret File** (Render Dashboard → service → Environment → Secret
   Files) mounted at `/etc/secrets/google-service-account.json` — this path
   matches the default in `render.yaml`.
6. Deploy. Render builds with `pip install -r requirements.txt` and starts
   with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
7. Confirm health: `https://<your-service>.onrender.com/api/v1/health`.

### Option B: Manual Web Service

If you'd rather not use the Blueprint: **New → Web Service**, connect the
repo, set:
- **Root Directory**: `backend`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Health Check Path**: `/api/v1/health`

Then add the same environment variables as above manually.

### Reminder Notifications (Cron Job)

`POST /api/v1/notifications/check-reminders` scans due task reminders and
creates notifications — it needs to be called periodically since this
backend has no built-in scheduler. On Render:

**New → Cron Job**, pointed at your backend, running e.g. every 5 minutes:

```bash
curl -X POST https://<your-service>.onrender.com/api/v1/notifications/check-reminders \
  -H "X-User-Id: <system or per-user id>"
```

(In production, once auth lands, this would iterate over all users server-side
rather than being called per-user — noted as follow-up work.)

## Frontend → Vercel

1. In the Vercel Dashboard: **Add New → Project**, import the repo.
2. Set **Root Directory** to `frontend`.
3. Vercel auto-detects Next.js (confirmed by `frontend/vercel.json`).
4. Add environment variables (Project → Settings → Environment Variables),
   matching `frontend/.env.local.example`:
   - `NEXT_PUBLIC_API_BASE_URL` → your Render backend URL + `/api/v1`
     (e.g. `https://enterprise-ai-agent-backend.onrender.com/api/v1`)
   - `NEXT_PUBLIC_FIREBASE_*` (all six)
   - `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`
5. Deploy.

## Post-Deploy Checklist

- [ ] Backend `/api/v1/health` returns `200`
- [ ] `GOOGLE_REDIRECT_URI` in Render env **and** in Google Cloud Console's
      OAuth client match the production callback URL exactly (not localhost)
- [ ] `GOOGLE_POST_AUTH_REDIRECT_URL` / `GOOGLE_POST_AUTH_ERROR_REDIRECT_URL`
      point at the deployed Vercel domain
- [ ] `FRONTEND_ORIGINS` on the backend includes the Vercel production URL
      (and any preview-deployment domains you want to allow), so CORS
      doesn't block the frontend
- [ ] `TOKEN_ENCRYPTION_KEY` / `OAUTH_STATE_SECRET` in production are
      **different** from local dev values and stored only in Render's env
- [ ] Supabase Storage bucket `user-uploads` exists in the production
      Supabase project (each environment/project needs its own)
- [ ] All three additive SQL migrations have been run against the
      **production** Supabase project, not just local/dev
- [ ] Google OAuth consent screen is out of "Testing" (or your account is
      listed as a test user) for the Google accounts that will actually use
      the deployed app
- [ ] Reminder cron job configured and hitting the production URL

## Environments

Keep entirely separate Supabase projects, Google OAuth clients (different
redirect URIs), and secrets for local/dev vs. production. Never reuse a
`TOKEN_ENCRYPTION_KEY` across environments — if it's ever rotated or
mismatched, every stored Google connection in that environment becomes
unreadable and users must reconnect.
