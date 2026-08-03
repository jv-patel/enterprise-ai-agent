# Enterprise AI Personal Agent

A production-grade AI personal agent: Next.js 15 / React 19 / TypeScript
frontend, FastAPI / LangGraph backend, Supabase Postgres, Firebase Auth,
Google Gemini (with OpenRouter fallback support), and deep integration with
Gmail, Google Calendar, Google Drive, Voice AI, Vision AI, and document
intelligence — orchestrated by a multi-agent system.

📄 See also: [docs/INSTALLATION.md](docs/INSTALLATION.md) ·
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) ·
[docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) ·
[docs/GOOGLE_CLOUD_SETUP.md](docs/GOOGLE_CLOUD_SETUP.md)

## What's Implemented

### Multi-Agent System
A **Coordinator Agent** classifies each request and routes it to a
specialist agent (or an explicit `agent_name` override), all sharing one
LangGraph plan/act/retry engine with a scoped subset of the tool registry:

| Agent | Scope |
|---|---|
| Assistant Agent | General-purpose, full tool registry |
| Email Agent | Gmail: send, read, reply, delete |
| Calendar Agent | Google Calendar: create/update/delete events, upcoming meetings |
| Research Agent | Web search + long-term memory search |
| Vision Agent | Image analysis / OCR on uploaded images |
| Notes Agent | Notes CRUD |
| Task Agent | Tasks/reminders CRUD |
| Coordinator Agent | Routes to the above; itself is `agents/router.py` + `agents/coordinator.py` |

Every run is logged step-by-step (`route → plan → tool_call → tool_result →
retry/error → final_answer`) to `agent_runs` / `agent_logs`, giving a full
execution timeline per request.

### AI Chat & Memory
Conversation memory (per-chat history), long-term memory (pgvector semantic
search + "save this" / "search my memory" tools), and full context awareness
across turns.

### Google Workspace Integrations
Gmail, Calendar, and Drive — via per-user OAuth with encrypted token storage
and automatic refresh. See [docs/GOOGLE_CLOUD_SETUP.md](docs/GOOGLE_CLOUD_SETUP.md).

### Voice AI
Speech-to-Text (batch + real-time streaming via WebSocket), Text-to-Speech,
full voice-chat round trip, microphone capture and stop-speaking controls in
the frontend.

### Vision AI
Gemini Vision-powered image understanding, OCR, screenshot analysis, and
chart/graph analysis.

### File Intelligence
PDF / DOCX / TXT / CSV / XLSX upload, text extraction, summarization, and
grounded Q&A.

### Dashboard (backend)
Usage analytics, AI statistics (success rate, per-agent/per-tool usage),
activity feed, execution timeline, notifications (incl. task reminders), and
user profile/settings.

### Performance & Reliability
In-memory TTL caching (weather, web search, dashboard analytics),
count-only/RPC-aggregated queries instead of row-by-row aggregation,
composite DB indexes, per-tool retry with backoff, and a request-tracing
middleware that stamps every response (and error) with a correlation ID.

### Deployment
Render Blueprint (`render.yaml`) for the backend, Vercel config
(`frontend/vercel.json`) for the frontend. See
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Project Structure

```
enterprise-ai-agent/
├── frontend/                      Next.js 15 app (App Router)
│   ├── app/                        routes & layouts
│   ├── components/
│   │   ├── voice/                   mic recorder, stop-speaking, streaming transcript
│   │   ├── files/                   upload widget, summarize/ask panel
│   │   ├── vision/                  image analysis panel
│   │   └── theme-provider.tsx
│   ├── lib/                        api client, audio recorder, ws voice client, cn
│   ├── store/                      Zustand stores (ui, voice)
│   └── vercel.json
├── backend/                       FastAPI app
│   └── app/
│       ├── api/                     HTTP route handlers (one file per domain)
│       ├── agents/
│       │   ├── graph.py               core LangGraph plan/act/retry engine
│       │   ├── coordinator.py         Coordinator Agent (routes + drives a run)
│       │   ├── router.py              intent classifier
│       │   ├── specialized_agents.py  per-agent tool scope + system prompts
│       │   └── tools/                 one tool module per capability
│       ├── core/                    config, logging, exceptions, cache, middleware, crypto
│       ├── database/                Supabase client + schema*.sql (additive migrations)
│       ├── schemas/                 Pydantic request/response models
│       └── services/                integrations (Gemini, Google APIs, Voice, Vision, ...)
├── docs/                           setup/deployment/API documentation
├── render.yaml
└── README.md
```

## Quick Start

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for full details. Short version:

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in real credentials
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
cp .env.local.example .env.local   # fill in real credentials
npm run dev
```

### Database

Run these against your Supabase project, **in order** (SQL Editor or
`supabase db push`):

1. `backend/app/database/schema.sql`
2. `backend/app/database/schema_phase2_agent.sql`
3. `backend/app/database/schema_phase5_enterprise.sql`

(Phase 3/4 introduced no new SQL — `google_credentials` and `uploaded_files`
were already defined in `schema.sql`.)

## Roadmap

1. ✅ Project scaffolding (structure, configs, DB schema, health check)
2. ✅ LangGraph AI agent (planning, memory, tool calling, retries, execution logs)
3. ✅ Google integrations (Gmail, Calendar, Drive) + OAuth
4. ✅ Voice AI, Vision AI, File Intelligence
5. ✅ Multi-agent system, Dashboard backend, Performance, Deployment configs, full documentation
6. ⬜ Firebase email + Google OAuth **sign-in** (replaces the interim `X-User-Id` header auth)
7. ⬜ Dashboard/Chat frontend pages (the backend APIs and several standalone components already exist; a full page assembling them is still open)
8. ⬜ Security hardening pass (rate limiting middleware, stricter input validation, secrets audit)

## Interim Authentication Note

Until Phase 6 (Firebase auth) lands, every authenticated endpoint identifies
the caller via an `X-User-Id` header (see `backend/app/core/dependencies.py`)
— the frontend is expected to send the Supabase `users.id`. This keeps every
route's authorization logic identical to what it will be after Phase 6; only
the identity-resolution dependency itself will change.
