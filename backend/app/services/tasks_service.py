"""Tasks + reminders CRUD, shared by app/api/tasks.py and the agent's task tool."""
from typing import Any

from app.core.exceptions import NotFoundError
from app.database.supabase_client import get_supabase

VALID_STATUSES = {"pending", "in_progress", "completed", "cancelled"}
VALID_PRIORITIES = {"low", "medium", "high"}


async def create_task(
    *,
    user_id: str,
    title: str,
    description: str | None = None,
    priority: str = "medium",
    due_at: str | None = None,
    remind_at: str | None = None,
) -> dict[str, Any]:
    if priority not in VALID_PRIORITIES:
        priority = "medium"

    supabase = get_supabase()
    response = (
        supabase.table("tasks")
        .insert(
            {
                "user_id": user_id,
                "title": title,
                "description": description,
                "priority": priority,
                "due_at": due_at,
                "remind_at": remind_at,
            }
        )
        .execute()
    )
    return response.data[0]


async def list_tasks(user_id: str, status: str | None = None) -> list[dict[str, Any]]:
    supabase = get_supabase()
    query = supabase.table("tasks").select("*").eq("user_id", user_id).order("due_at", desc=False)
    if status:
        query = query.eq("status", status)
    return query.execute().data


async def get_task(user_id: str, task_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    response = supabase.table("tasks").select("*").eq("id", task_id).eq("user_id", user_id).limit(1).execute()
    if not response.data:
        raise NotFoundError(f"Task {task_id} not found.")
    return response.data[0]


async def update_task(
    *,
    user_id: str,
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    due_at: str | None = None,
    remind_at: str | None = None,
) -> dict[str, Any]:
    await get_task(user_id, task_id)
    updates: dict[str, Any] = {}
    if title is not None:
        updates["title"] = title
    if description is not None:
        updates["description"] = description
    if status is not None and status in VALID_STATUSES:
        updates["status"] = status
    if priority is not None and priority in VALID_PRIORITIES:
        updates["priority"] = priority
    if due_at is not None:
        updates["due_at"] = due_at
    if remind_at is not None:
        updates["remind_at"] = remind_at

    supabase = get_supabase()
    response = supabase.table("tasks").update(updates).eq("id", task_id).eq("user_id", user_id).execute()
    return response.data[0]


async def delete_task(user_id: str, task_id: str) -> None:
    await get_task(user_id, task_id)
    supabase = get_supabase()
    supabase.table("tasks").delete().eq("id", task_id).eq("user_id", user_id).execute()


async def list_upcoming_reminders(user_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    response = (
        supabase.table("tasks")
        .select("*")
        .eq("user_id", user_id)
        .not_.is_("remind_at", "null")
        .in_("status", ["pending", "in_progress"])
        .order("remind_at", desc=False)
        .execute()
    )
    return response.data
