"""
Activity feed for the dashboard.

Rather than introducing a separate audit-log table that every write path
would need to remember to update, this reads the existing `agent_logs`
table (joined to `agent_runs` for ownership) filtered to `tool_result`
entries — every user-visible action (sending an email, creating an event,
editing a note, etc.) already flows through a tool call, so this is a
complete activity trail with zero additional write paths to maintain.
"""
from typing import Any

from app.database.supabase_client import get_supabase

DEFAULT_LIMIT = 30


async def list_activity_feed(user_id: str, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    supabase = get_supabase()
    response = (
        supabase.table("agent_logs")
        .select("id, run_id, agent_name, action_type, detail, created_at, agent_runs!inner(user_id, chat_id)")
        .eq("agent_runs.user_id", user_id)
        .eq("action_type", "tool_result")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )

    activity: list[dict[str, Any]] = []
    for row in response.data:
        detail = row.get("detail") or {}
        activity.append(
            {
                "id": row["id"],
                "run_id": row["run_id"],
                "agent_name": row["agent_name"],
                "tool": detail.get("tool"),
                "success": detail.get("success", True),
                "created_at": row["created_at"],
            }
        )
    return activity
