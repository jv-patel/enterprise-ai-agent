"""
Chat + chat_messages persistence.

This is the "conversation memory" and "context awareness" layer: every
agent run reads recent messages from here to build context, and writes the
user/assistant turns back once the run completes.
"""
from typing import Any

from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase

logger = get_logger(__name__)

DEFAULT_HISTORY_LIMIT = 20


async def get_or_create_chat(user_id: str, chat_id: str | None, title_hint: str) -> dict[str, Any]:
    supabase = get_supabase()

    if chat_id:
        response = (
            supabase.table("chats")
            .select("*")
            .eq("id", chat_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            raise NotFoundError(f"Chat {chat_id} not found for this user.")
        return response.data[0]

    title = (title_hint[:60] + "...") if len(title_hint) > 60 else title_hint
    response = (
        supabase.table("chats")
        .insert({"user_id": user_id, "title": title or "New Chat"})
        .execute()
    )
    return response.data[0]


async def list_chats(user_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    response = (
        supabase.table("chats")
        .select("*")
        .eq("user_id", user_id)
        .order("updated_at", desc=True)
        .execute()
    )
    return response.data


async def get_recent_messages(chat_id: str, limit: int = DEFAULT_HISTORY_LIMIT) -> list[dict[str, Any]]:
    supabase = get_supabase()
    response = (
        supabase.table("chat_messages")
        .select("role, content, created_at")
        .eq("chat_id", chat_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return list(reversed(response.data))


async def append_message(
    *,
    chat_id: str,
    user_id: str,
    role: str,
    content: str,
    tool_calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("chat_messages")
        .insert(
            {
                "chat_id": chat_id,
                "user_id": user_id,
                "role": role,
                "content": content,
                "tool_calls": tool_calls,
            }
        )
        .execute()
    )
    supabase.table("chats").update({"updated_at": "now()"}).eq("id", chat_id).execute()
    return response.data[0]


async def search_chats(user_id: str, query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Full-text search across a user's past chat messages (used by the
    'search previous chats' agent tool)."""
    supabase = get_supabase()
    response = (
        supabase.table("chat_messages")
        .select("chat_id, role, content, created_at")
        .eq("user_id", user_id)
        .ilike("content", f"%{query}%")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data
