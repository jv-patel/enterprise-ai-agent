-- ============================================================================
-- Phase 2 additive migration — Agent long-term memory search.
-- Run AFTER schema.sql. Does not modify any Phase 1 table.
-- ============================================================================

-- Cosine-similarity search over chat_memory.embedding (pgvector), scoped to a
-- single user. Used by the "search previous memories" agent tool.
create or replace function public.match_chat_memory(
    p_user_id uuid,
    p_query_embedding vector(768),
    p_match_count integer default 5
)
returns table (
    id uuid,
    chat_id uuid,
    memory_type text,
    content text,
    similarity float,
    created_at timestamptz
)
language sql
stable
as $$
    select
        cm.id,
        cm.chat_id,
        cm.memory_type,
        cm.content,
        1 - (cm.embedding <=> p_query_embedding) as similarity,
        cm.created_at
    from public.chat_memory cm
    where cm.user_id = p_user_id
      and cm.embedding is not null
    order by cm.embedding <=> p_query_embedding
    limit p_match_count;
$$;

create index if not exists idx_chat_memory_embedding
    on public.chat_memory using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);
