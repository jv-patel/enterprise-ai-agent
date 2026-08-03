# Google Cloud Setup Guide — Gmail, Calendar & Drive Integration

This guide walks through everything needed in Google Cloud Console for the
Enterprise AI Personal Agent's Google integrations (Phase 3) to work end to
end, from project creation through production verification.

---

## 1. Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com/).
2. Click the project dropdown (top left) → **New Project**.
3. Name it (e.g. `enterprise-ai-agent`) and click **Create**.
4. Select the new project once it's created.

---

## 2. Enable the Required APIs

Go to **APIs & Services → Library** and enable each of the following:

| API | Used for |
|---|---|
| **Gmail API** | Send / read inbox / reply / delete (trash) |
| **Google Calendar API** | Create / update / delete events, upcoming meetings |
| **Google Drive API** | Search files, read file content |

Search each by name in the library, open it, and click **Enable**.

---

## 3. Configure the OAuth Consent Screen

Go to **APIs & Services → OAuth consent screen**.

1. **User type**:
   - **Internal** if you're on Google Workspace and only your organization's
     users will use the app (no verification required, but limited to your
     org).
   - **External** for a general consumer/personal-account app (this is the
     common case for this project).
2. Fill in the required fields: app name, user support email, developer
   contact email.
3. **Scopes**: click **Add or Remove Scopes** and add the following (these
   match exactly what `google_oauth_service.py` requests):
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/calendar.events`
   - `https://www.googleapis.com/auth/drive.readonly`
4. **Test users** (while in "Testing" publishing status): add every Google
   account (including your own) that will authorize the app. Unverified apps
   in Testing mode can **only** be used by accounts listed here.
5. Save.

### About scope sensitivity

- `gmail.send`, `gmail.modify`, `calendar.events`, and `drive.readonly` are
  classified by Google as **sensitive** or **restricted** scopes.
- While your app is in **Testing**, any of the test users you added can
  authorize it immediately — no review needed.
- To move to **Production** (so any Google user can connect, not just test
  users), Google requires an **OAuth verification review**, and for
  restricted scopes, often a third-party **security assessment (CASA)**.
  Budget several business days to weeks for this if you plan to launch
  publicly. For internal or personal use, staying in Testing (with test
  users added) is sufficient indefinitely.
- **Unverified apps in Testing mode**: as of Google's 2022 policy change,
  refresh tokens issued to unverified apps expire after **7 days** unless the
  app has completed verification. For any real deployment (even
  internal/staging), complete verification before relying on long-lived
  Google connections — otherwise users will need to reconnect weekly.

---

## 4. Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. **Application type**: `Web application`.
4. **Name**: e.g. `Enterprise AI Agent Backend`.
5. **Authorized redirect URIs** — add the exact callback URL the backend
   exposes:
   - Local development: `http://localhost:8000/api/v1/google/oauth/callback`
   - Production (Render): `https://<your-render-service>.onrender.com/api/v1/google/oauth/callback`

   This must match `GOOGLE_REDIRECT_URI` in `backend/.env` **exactly**,
   including scheme and trailing path — Google rejects any mismatch.
6. Click **Create**. Copy the generated **Client ID** and **Client Secret**.

---

## 5. Configure Backend Environment Variables

In `backend/.env` (copied from `backend/.env.example`):

```bash
GOOGLE_CLIENT_ID=<your client id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your client secret>
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/google/oauth/callback
GOOGLE_POST_AUTH_REDIRECT_URL=http://localhost:3000/dashboard/settings?google=connected
GOOGLE_POST_AUTH_ERROR_REDIRECT_URL=http://localhost:3000/dashboard/settings?google=error
```

### Secure Token Storage

Access and refresh tokens are encrypted before being written to the
`google_credentials` table (see `backend/app/core/crypto.py`), and the OAuth
`state` parameter is signed to prevent CSRF and tie the callback back to the
initiating user. Generate both secrets locally and put them in `.env`
(never commit them):

```bash
# TOKEN_ENCRYPTION_KEY — Fernet key used to encrypt stored tokens at rest
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# OAUTH_STATE_SECRET — any long random string, used to HMAC-sign the OAuth state
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

```bash
TOKEN_ENCRYPTION_KEY=<generated fernet key>
OAUTH_STATE_SECRET=<generated random secret>
```

If either of these is rotated, all existing stored Google connections become
unreadable/invalid and users must reconnect via `/google/oauth/authorize`.

---

## 6. Run the Additive Database Migration

`backend/app/database/schema_phase2_agent.sql` already created the
`chat_memory` vector search RPC in Phase 2. The `google_credentials` table
itself was defined in Phase 1's `schema.sql` — no further migration is
needed for this phase; just confirm it exists in Supabase (Table Editor →
`google_credentials`).

---

## 7. Connect a Google Account (Flow Walkthrough)

1. Frontend calls `GET /api/v1/google/oauth/authorize` (with the user's
   `X-User-Id` header) → backend returns `{ "authorization_url": "..." }`.
2. Frontend redirects the browser to that URL. The user signs in and
   consents to the requested scopes on Google's own page.
3. Google redirects back to `GOOGLE_REDIRECT_URI` with `code` and `state`
   query params.
4. The backend's `/google/oauth/callback` exchanges the code for tokens,
   encrypts and stores them, then redirects the browser to
   `GOOGLE_POST_AUTH_REDIRECT_URL`.
5. From then on, `GET /api/v1/google/status` reports `{"connected": true, ...}`,
   and the agent's Gmail/Calendar/Drive tools (and the equivalent REST
   endpoints) work automatically — access tokens are refreshed transparently
   when they expire.

---

## 8. Common Setup Errors

| Symptom | Cause | Fix |
|---|---|---|
| `redirect_uri_mismatch` | The URI Google receives doesn't exactly match one in your OAuth client's Authorized redirect URIs | Copy `GOOGLE_REDIRECT_URI` from `.env` verbatim into the Cloud Console credential |
| `access_denied` during consent | Signed-in Google account isn't in the Test users list (Testing publishing status) | Add the account under OAuth consent screen → Test users |
| Refresh token missing after reconnect | Google only issues a refresh token on the **first** consent grant unless `prompt=consent` is forced | Already handled — `google_oauth_service.py` always passes `prompt=consent` |
| `google_reauth_required` error from the API | Refresh token missing/revoked, or the unverified-app 7-day token expiry was hit | User must reconnect via `/google/oauth/authorize` |
| `403 insufficientPermissions` from Gmail/Calendar/Drive API | Requested scope wasn't granted or API wasn't enabled | Re-check step 2 (APIs enabled) and step 3 (scopes added), then reconnect |

---

## 9. Production Checklist

- [ ] All three APIs enabled (Gmail, Calendar, Drive)
- [ ] OAuth consent screen scopes match `ALL_SCOPES` in `google_oauth_service.py`
- [ ] Redirect URI in Cloud Console matches `GOOGLE_REDIRECT_URI` exactly (prod value, not localhost)
- [ ] `TOKEN_ENCRYPTION_KEY` and `OAUTH_STATE_SECRET` set to strong, unique values in the Render environment (not the same as local dev)
- [ ] App submitted for OAuth verification if it will be used by accounts outside your test-user list
- [ ] `GOOGLE_POST_AUTH_REDIRECT_URL` / `GOOGLE_POST_AUTH_ERROR_REDIRECT_URL` point at the deployed frontend domain, not localhost

---

## 10. Voice AI Setup (Speech-to-Text / Text-to-Speech) — Phase 4

Unlike Gmail/Calendar/Drive (which use per-user OAuth consent), Speech-to-Text
and Text-to-Speech are called **server-to-server** with a GCP **service
account**, since there's no per-user data being accessed — just raw audio in,
text out (and vice versa).

1. Enable the APIs: **APIs & Services → Library** → enable **Cloud
   Speech-to-Text API** and **Cloud Text-to-Speech API**.
2. Create a service account: **IAM & Admin → Service Accounts → Create
   Service Account**. Name it e.g. `voice-ai-backend`.
3. Grant it the roles **Cloud Speech Client** and **Cloud Text-to-Speech
   User** (or broader `roles/editor` for local dev only — use least-privilege
   roles in production).
4. **Keys → Add Key → Create new key → JSON**. This downloads a service
   account key file — treat it like a password.
5. Set the environment variable so the `google-cloud-speech` /
   `google-cloud-texttospeech` client libraries pick it up automatically:

   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account-key.json
   ```

   On Render, upload the JSON as a **Secret File** and point
   `GOOGLE_APPLICATION_CREDENTIALS` at its mounted path (e.g.
   `/etc/secrets/voice-ai-key.json`).
6. Never commit the key file — it's already excluded by nothing in
   particular, so explicitly keep it out of the repo (add its filename to
   `.gitignore` if you store it locally under the project directory).

### Supabase Storage bucket (used by Voice AI's file-based tools indirectly, and directly by Vision/File Intelligence)

Image and document uploads (Phase 4) are stored in Supabase Storage, not
just the database. Create the bucket once:

1. Supabase Dashboard → **Storage → New Bucket**.
2. Name it to match `SUPABASE_STORAGE_BUCKET` in `.env` (default
   `user-uploads`).
3. Leave it **private** (not public) — the backend accesses it via the
   service-role key, and downstream file/vision endpoints always check
   `user_id` ownership before returning any content.

