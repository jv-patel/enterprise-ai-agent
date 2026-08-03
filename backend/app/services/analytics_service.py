"""
Dashboard analytics: usage counts and AI statistics.

Uses `count="exact"` with `limit(1)` for cheap tallies — PostgREST returns
the true total match count via the Content-Range header independent of the
applied limit, so this avoids transferring full row sets just to count them
— and the `get_tool_usage_stats` / `get_agent_usage_stats` RPCs (see
schema_phase5_enterprise.sql) so aggregation happens in Postgres rather than
in application code. Results are cached briefly since dashboard views
tolerate a few seconds of staleness far better than they tolerate slow page
loads.
"""
from typing import Any

from app.core.cache import cached
from app.database.supabase_client import get_supabase

ANALYTICS_CACHE_TTL_SECONDS = 60


def _count(table: str, user_id: str) -> int:
    supabase = get_supabase()
    # count="exact" returns the true total match count via PostgREST's
    # Content-Range header regardless of the row limit applied, so limit(1)
    # keeps the response payload minimal without affecting the count.
    response = supabase.table(table).select("id", count="exact").eq("user_id", user_id).limit(1).execute()
    return response.count or 0


@cached(ANALYTICS_CACHE_TTL_SECONDS, key_prefix="usage_analytics")
async def get_usage_analytics(user_id: str) -> dict[str, Any]:
    supabase = get_supabase()

    chats_count = _count("chats", user_id)
    notes_count = _count("notes", user_id)
    tasks_count = _count("tasks", user_id)
    files_count = _count("uploaded_files", user_id)
    agent_runs_count = _count("agent_runs", user_id)

    messages_response = (
        supabase.table("chat_messages")
        .select("id", count="exact")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )

    return {
        "total_chats": chats_count,
        "total_messages": messages_response.count or 0,
        "total_notes": notes_count,
        "total_tasks": tasks_count,
        "total_files_uploaded": files_count,
        "total_agent_runs": agent_runs_count,
    }


@cached(ANALYTICS_CACHE_TTL_SECONDS, key_prefix="ai_statistics")
async def get_ai_statistics(user_id: str) -> dict[str, Any]:
    supabase = get_supabase()

    agent_stats = supabase.rpc("get_agent_usage_stats", {"p_user_id": user_id}).execute().data or []
    tool_stats = supabase.rpc("get_tool_usage_stats", {"p_user_id": user_id, "p_limit": 10}).execute().data or []

    total_runs = sum(row["run_count"] for row in agent_stats)
    total_completed = sum(row["completed_count"] for row in agent_stats)
    total_failed = sum(row["failed_count"] for row in agent_stats)
    success_rate = round((total_completed / total_runs) * 100, 1) if total_runs else 0.0

    return {
        "total_runs": total_runs,
        "completed_runs": total_completed,
        "failed_runs": total_failed,
        "success_rate_percent": success_rate,
        "runs_by_agent": agent_stats,
        "top_tools": tool_stats,
    }
