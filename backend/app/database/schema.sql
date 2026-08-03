-- ============================================================================
-- Enterprise AI Personal Agent — Supabase PostgreSQL Schema
-- Run this once against your Supabase project (SQL Editor or `supabase db push`).
-- Row Level Security is enabled everywhere; access is brokered by the FastAPI
-- backend using the service-role key, with `firebase_uid` as the tenant key.
-- ============================================================================

create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";
create extension if not exists "vector";

-- ----------------------------------------------------------------------------
-- users: mirrors Firebase-authenticated identities
-- ----------------------------------------------------------------------------
create table if not exists public.users (
    id              uuid primary key default uuid_generate_v4(),
    firebase_uid    text unique not null,
    email           text unique not null,
    display_name    text,
    photo_url       text,
    auth_provider   text not null default 'password',
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- user_settings: theme, preferences, and per-user configuration
-- ----------------------------------------------------------------------------
create table if not exists public.user_settings (
    user_id             uuid primary key references public.users(id) on delete cascade,
    theme               text not null default 'system' check (theme in ('light', 'dark', 'system')),
    preferred_ai_model  text not null default 'gemini-2.0-flash',
    preferred_provider  text not null default 'gemini' check (preferred_provider in ('gemini', 'openrouter')),
    voice_enabled       boolean not null default true,
    notification_prefs  jsonb not null default '{}'::jsonb,
    updated_at          timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- chats / chat_messages: multi-conversation AI chat with memory
-- ----------------------------------------------------------------------------
create table if not exists public.chats (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references public.users(id) on delete cascade,
    title       text not null default 'New Chat',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create table if not exists public.chat_messages (
    id          uuid primary key default uuid_generate_v4(),
    chat_id     uuid not null references public.chats(id) on delete cascade,
    user_id     uuid not null references public.users(id) on delete cascade,
    role        text not null check (role in ('user', 'assistant', 'system', 'tool')),
    content     text not null,
    tool_calls  jsonb,
    attachments jsonb,
    created_at  timestamptz not null default now()
);

create table if not exists public.chat_memory (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references public.users(id) on delete cascade,
    chat_id     uuid references public.chats(id) on delete cascade,
    memory_type text not null check (memory_type in ('fact', 'preference', 'summary')),
    content     text not null,
    embedding   vector(768),
    created_at  timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- agent_runs / agent_logs: LangGraph execution timeline
-- ----------------------------------------------------------------------------
create table if not exists public.agent_runs (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null references public.users(id) on delete cascade,
    chat_id         uuid references public.chats(id) on delete cascade,
    agent_name      text not null,
    goal            text not null,
    status          text not null default 'running' check (status in ('running', 'completed', 'failed', 'retrying')),
    started_at      timestamptz not null default now(),
    completed_at    timestamptz
);

create table if not exists public.agent_logs (
    id          uuid primary key default uuid_generate_v4(),
    run_id      uuid not null references public.agent_runs(id) on delete cascade,
    step_index  integer not null,
    agent_name  text not null,
    action_type text not null check (action_type in ('plan', 'tool_call', 'tool_result', 'retry', 'error', 'final_answer')),
    detail      jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- google_credentials: encrypted OAuth tokens for Gmail / Calendar / Drive
-- ----------------------------------------------------------------------------
create table if not exists public.google_credentials (
    user_id         uuid primary key references public.users(id) on delete cascade,
    access_token    text not null,
    refresh_token   text not null,
    scopes          text[] not null default '{}',
    expires_at      timestamptz not null,
    updated_at      timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- notes
-- ----------------------------------------------------------------------------
create table if not exists public.notes (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references public.users(id) on delete cascade,
    title       text not null,
    content     text not null default '',
    tags        text[] not null default '{}',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- tasks / reminders
-- ----------------------------------------------------------------------------
create table if not exists public.tasks (
    id           uuid primary key default uuid_generate_v4(),
    user_id      uuid not null references public.users(id) on delete cascade,
    title        text not null,
    description  text,
    status       text not null default 'pending' check (status in ('pending', 'in_progress', 'completed', 'cancelled')),
    priority     text not null default 'medium' check (priority in ('low', 'medium', 'high')),
    due_at       timestamptz,
    remind_at    timestamptz,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- uploaded_files: PDF / DOCX / TXT / CSV / XLSX ingestion + summaries
-- ----------------------------------------------------------------------------
create table if not exists public.uploaded_files (
    id              uuid primary key default uuid_generate_v4(),
    user_id         uuid not null references public.users(id) on delete cascade,
    chat_id         uuid references public.chats(id) on delete cascade,
    file_name       text not null,
    file_type       text not null,
    storage_path    text not null,
    extracted_text  text,
    summary         text,
    created_at      timestamptz not null default now()
);

-- ----------------------------------------------------------------------------
-- indexes
-- ----------------------------------------------------------------------------
create index if not exists idx_chats_user_id on public.chats(user_id);
create index if not exists idx_chat_messages_chat_id on public.chat_messages(chat_id);
create index if not exists idx_chat_memory_user_id on public.chat_memory(user_id);
create index if not exists idx_agent_runs_user_id on public.agent_runs(user_id);
create index if not exists idx_agent_logs_run_id on public.agent_logs(run_id);
create index if not exists idx_notes_user_id on public.notes(user_id);
create index if not exists idx_tasks_user_id on public.tasks(user_id);
create index if not exists idx_uploaded_files_user_id on public.uploaded_files(user_id);

-- ----------------------------------------------------------------------------
-- row level security
-- ----------------------------------------------------------------------------
alter table public.users enable row level security;
alter table public.user_settings enable row level security;
alter table public.chats enable row level security;
alter table public.chat_messages enable row level security;
alter table public.chat_memory enable row level security;
alter table public.agent_runs enable row level security;
alter table public.agent_logs enable row level security;
alter table public.google_credentials enable row level security;
alter table public.notes enable row level security;
alter table public.tasks enable row level security;
alter table public.uploaded_files enable row level security;

-- The backend accesses these tables exclusively via the service-role key,
-- which bypasses RLS by design. No public/anon policies are defined, so
-- direct client access from the frontend's anon key is fully denied.

-- ----------------------------------------------------------------------------
-- updated_at trigger helper
-- ----------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger trg_users_updated_at before update on public.users
    for each row execute function public.set_updated_at();
create trigger trg_chats_updated_at before update on public.chats
    for each row execute function public.set_updated_at();
create trigger trg_notes_updated_at before update on public.notes
    for each row execute function public.set_updated_at();
create trigger trg_tasks_updated_at before update on public.tasks
    for each row execute function public.set_updated_at();
