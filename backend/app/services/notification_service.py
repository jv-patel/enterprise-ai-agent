"""
Notifications: reminders, agent-run failures, and other user-facing alerts.

`check_due_reminders` is meant to be invoked periodically (a Render Cron Job
hitting `POST /notifications/check-reminders`, or an equivalent scheduler —
see docs/DEPLOYMENT.md) since this backend has no built-in background
scheduler. It's idempotent per reminder: once a task's reminder fires, its
`remind_at` is cleared so it won't generate a duplicate notification on the
next check.
"""
from datetime import datetime, timezone
from typing import Any

from app.core.exceptions import NotFoundError
from app.database.supabase_client import get_supabase

DEFAULT_LIMIT = 50


async def list_notifications(user_id: str, unread_only: bool = False, limit: int = DEFAULT_LIMIT) -> list[dict[str, Any]]:
    supabase = get_supabase()
    query = (
        supabase.table("notifications")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if unread_only:
        query = query.eq("read", False)
    return query.execute().data


async def create_notification(
    *, user_id: str, type_: str, title: str, message: str, metadata: dict[str, Any] | None = None
) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("notifications")
        .insert({"user_id": user_id, "type": type_, "title": title, "message": message, "metadata": metadata or {}})
        .execute()
    )
    return response.data[0]


async def mark_notification_read(user_id: str, notification_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("notifications")
        .update({"read": True})
        .eq("id", notification_id)
        .eq("user_id", user_id)
        .execute()
    )
    if not response.data:
        raise NotFoundError(f"Notification {notification_id} not found.")
    return response.data[0]


async def mark_all_read(user_id: str) -> int:
    supabase = get_supabase()
    response = (
        supabase.table("notifications").update({"read": True}).eq("user_id", user_id).eq("read", False).execute()
    )
    return len(response.data)


async def check_due_reminders(user_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    now_iso = datetime.now(timezone.utc).isoformat()

    due_tasks = (
        supabase.table("tasks")
        .select("id, title, remind_at")
        .eq("user_id", user_id)
        .not_.is_("remind_at", "null")
        .lte("remind_at", now_iso)
        .in_("status", ["pending", "in_progress"])
        .execute()
    ).data

    created: list[dict[str, Any]] = []
    for task in due_tasks:
        notification = await create_notification(
            user_id=user_id,
            type_="reminder",
            title="Task reminder",
            message=f"Reminder: {task['title']}",
            metadata={"task_id": task["id"]},
        )
        created.append(notification)
        # Clear remind_at so this reminder doesn't fire again on the next check.
        supabase.table("tasks").update({"remind_at": None}).eq("id", task["id"]).execute()

    return created
