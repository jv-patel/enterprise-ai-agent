"""
Persists agent_runs / agent_logs so every agent execution has a durable,
inspectable timeline (plan → tool_call → tool_result → retry → final_answer).
"""
from typing import Any

from app.core.exceptions import NotFoundError
from app.database.supabase_client import get_supabase


async def start_run(*, user_id: str, chat_id: str | None, agent_name: str, goal: str) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("agent_runs")
        .insert({"user_id": user_id, "chat_id": chat_id, "agent_name": agent_name, "goal": goal, "status": "running"})
        .execute()
    )
    return response.data[0]


async def log_step(
    *,
    run_id: str,
    step_index: int,
    agent_name: str,
    action_type: str,
    detail: dict[str, Any],
) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("agent_logs")
        .insert(
            {
                "run_id": run_id,
                "step_index": step_index,
                "agent_name": agent_name,
                "action_type": action_type,
                "detail": detail,
            }
        )
        .execute()
    )
    return response.data[0]


async def complete_run(*, run_id: str, status: str) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("agent_runs")
        .update({"status": status, "completed_at": "now()"})
        .eq("id", run_id)
        .execute()
    )
    if not response.data:
        raise NotFoundError(f"Agent run {run_id} not found.")
    return response.data[0]


async def get_run(run_id: str, user_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("agent_runs").select("*").eq("id", run_id).eq("user_id", user_id).limit(1).execute()
    )
    if not response.data:
        raise NotFoundError(f"Agent run {run_id} not found.")
    return response.data[0]


async def get_run_timeline(run_id: str, user_id: str) -> list[dict[str, Any]]:
    await get_run(run_id, user_id)
    supabase = get_supabase()
    response = (
        supabase.table("agent_logs")
        .select("*")
        .eq("run_id", run_id)
        .order("step_index", desc=False)
        .execute()
    )
    return response.data


async def list_runs(user_id: str, chat_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    supabase = get_supabase()
    query = (
        supabase.table("agent_runs")
        .select("*")
        .eq("user_id", user_id)
        .order("started_at", desc=True)
        .limit(limit)
    )
    if chat_id:
        query = query.eq("chat_id", chat_id)
    return query.execute().data
