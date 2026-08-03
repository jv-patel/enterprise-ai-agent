"""
Long-term memory: durable facts/preferences/summaries that outlive a single
chat, embedded with Gemini and searched via the `match_chat_memory` RPC
(see database/schema_phase2_agent.sql).
"""
from typing import Any

from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase
from app.services import gemini_service

logger = get_logger(__name__)

VALID_MEMORY_TYPES = {"fact", "preference", "summary"}


async def save_memory(
    *,
    user_id: str,
    content: str,
    memory_type: str = "fact",
    chat_id: str | None = None,
) -> dict[str, Any]:
    if memory_type not in VALID_MEMORY_TYPES:
        memory_type = "fact"

    embedding = await gemini_service.embed_text(content)
    supabase = get_supabase()
    response = (
        supabase.table("chat_memory")
        .insert(
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "memory_type": memory_type,
                "content": content,
                "embedding": embedding,
            }
        )
        .execute()
    )
    logger.info("Saved long-term memory for user %s (type=%s)", user_id, memory_type)
    return response.data[0]


async def search_memories(*, user_id: str, query: str, match_count: int = 5) -> list[dict[str, Any]]:
    query_embedding = await gemini_service.embed_text(query)
    supabase = get_supabase()
    response = supabase.rpc(
        "match_chat_memory",
        {
            "p_user_id": user_id,
            "p_query_embedding": query_embedding,
            "p_match_count": match_count,
        },
    ).execute()
    return response.data or []
