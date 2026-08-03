"""Notes CRUD, shared by app/api/notes.py and the agent's notes tool."""
from typing import Any

from app.core.exceptions import NotFoundError
from app.database.supabase_client import get_supabase


async def create_note(*, user_id: str, title: str, content: str = "", tags: list[str] | None = None) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("notes")
        .insert({"user_id": user_id, "title": title, "content": content, "tags": tags or []})
        .execute()
    )
    return response.data[0]


async def list_notes(user_id: str, tag: str | None = None) -> list[dict[str, Any]]:
    supabase = get_supabase()
    query = supabase.table("notes").select("*").eq("user_id", user_id).order("updated_at", desc=True)
    if tag:
        query = query.contains("tags", [tag])
    return query.execute().data


async def get_note(user_id: str, note_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("notes").select("*").eq("id", note_id).eq("user_id", user_id).limit(1).execute()
    )
    if not response.data:
        raise NotFoundError(f"Note {note_id} not found.")
    return response.data[0]


async def update_note(
    *, user_id: str, note_id: str, title: str | None = None, content: str | None = None, tags: list[str] | None = None
) -> dict[str, Any]:
    await get_note(user_id, note_id)
    updates: dict[str, Any] = {}
    if title is not None:
        updates["title"] = title
    if content is not None:
        updates["content"] = content
    if tags is not None:
        updates["tags"] = tags

    supabase = get_supabase()
    response = (
        supabase.table("notes").update(updates).eq("id", note_id).eq("user_id", user_id).execute()
    )
    return response.data[0]


async def delete_note(user_id: str, note_id: str) -> None:
    await get_note(user_id, note_id)
    supabase = get_supabase()
    supabase.table("notes").delete().eq("id", note_id).eq("user_id", user_id).execute()
