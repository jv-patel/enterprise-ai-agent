-- ============================================================================
-- Phase 5 additive migration — Multi-agent routing, Dashboard, Performance.
-- Run AFTER schema.sql and schema_phase2_agent.sql. Does not drop or modify
-- any existing column/table beyond the one documented ALTER below.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Allow the Coordinator Agent's routing decision to be logged alongside the
-- existing plan/tool_call/tool_result/retry/error/final_answer steps.
-- ----------------------------------------------------------------------------
alter table public.agent_logs drop constraint if exists agent_logs_action_type_check;
alter table public.agent_logs
    add constraint agent_logs_action_type_check
    check (action_type in ('route', 'plan', 'tool_call', 'tool_result', 'retry', 'error', 'final_answer'));

-- ----------------------------------------------------------------------------
-- notifications: reminders, agent-run failures, and other user-facing alerts
-- ----------------------------------------------------------------------------
create table if not exists public.notifications (
    id          uuid primary key default uuid_generate_v4(),
    user_id     uuid not null references public.users(id) on delete cascade,
    type        text not null check (type in ('reminder', 'agent_run', 'system', 'google')),
    title       text not null,
    message     text not null,
    read        boolean not null default false,
    metadata    jsonb not null default '{}'::jsonb,
    created_at  timestamptz not null default now()
);

alter table public.notifications enable row level security;
-- Accessed exclusively via the backend's service-role key, same as every
-- other table in this schema — no anon/public policies are defined.

create index if not exists idx_notifications_user_created
    on public.notifications(user_id, created_at desc);
create index if not exists idx_notifications_user_unread
    on public.notifications(user_id, read) where read = false;

-- ----------------------------------------------------------------------------
-- Performance: composite indexes for the query patterns introduced by the
-- multi-agent system and dashboard (avoids full-table scans as data grows).
-- ----------------------------------------------------------------------------
create index if not exists idx_chat_messages_chat_created
    on public.chat_messages(chat_id, created_at);
create index if not exists idx_agent_runs_user_started
    on public.agent_runs(user_id, started_at desc);
create index if not exists idx_agent_runs_user_agent_name
    on public.agent_runs(user_id, agent_name);
create index if not exists idx_agent_logs_run_step
    on public.agent_logs(run_id, step_index);

-- ----------------------------------------------------------------------------
-- Dashboard RPCs: aggregate stats computed in the database rather than
-- pulled row-by-row into the application (optimized queries).
-- ----------------------------------------------------------------------------
create or replace function public.get_tool_usage_stats(p_user_id uuid, p_limit integer default 10)
returns table (tool_name text, usage_count bigint)
language sql
stable
as $$
    select
        al.detail->>'tool' as tool_name,
        count(*) as usage_count
    from public.agent_logs al
    join public.agent_runs ar on ar.id = al.run_id
    where ar.user_id = p_user_id
      and al.action_type = 'tool_result'
      and al.detail->>'tool' is not null
    group by al.detail->>'tool'
    order by usage_count desc
    limit p_limit;
$$;

create or replace function public.get_agent_usage_stats(p_user_id uuid)
returns table (agent_name text, run_count bigint, completed_count bigint, failed_count bigint)
language sql
stable
as $$
    select
        ar.agent_name,
        count(*) as run_count,
        count(*) filter (where ar.status = 'completed') as completed_count,
        count(*) filter (where ar.status = 'failed') as failed_count
    from public.agent_runs ar
    where ar.user_id = p_user_id
    group by ar.agent_name;
$$;
