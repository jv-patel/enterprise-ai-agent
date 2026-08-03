"""Long-term memory tools: save important memories, search prior chats and memories."""
from app.agents.tools.registry import ToolSpec
from app.services import chat_service, memory_service


def build_save_memory_tool(*, user_id: str, chat_id: str | None) -> ToolSpec:
    async def save_memory(content: str, memory_type: str = "fact") -> dict:
        memory = await memory_service.save_memory(
            user_id=user_id, content=content, memory_type=memory_type, chat_id=chat_id
        )
        return {"memory_id": memory["id"], "saved": True}

    return ToolSpec(
        name="save_memory",
        description=(
            "Save an important, durable piece of information about the user for future "
            "conversations (a fact, stated preference, or summary). Use this when the user "
            "shares something worth remembering long-term."
        ),
        parameters={
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "The memory content to save."},
                "memory_type": {
                    "type": "string",
                    "enum": ["fact", "preference", "summary"],
                    "description": "Category of memory.",
                },
            },
            "required": ["content"],
        },
        handler=save_memory,
    )


def build_search_memory_tool(*, user_id: str) -> ToolSpec:
    async def search_memory(query: str) -> dict:
        memories = await memory_service.search_memories(user_id=user_id, query=query)
        past_chats = await chat_service.search_chats(user_id, query)
        return {
            "memories": [{"content": m["content"], "type": m["memory_type"]} for m in memories],
            "past_chat_matches": [
                {"role": c["role"], "content": c["content"], "created_at": c["created_at"]} for c in past_chats
            ],
        }

    return ToolSpec(
        name="search_memory",
        description=(
            "Search the user's long-term memories and previous chat history for information "
            "relevant to the current conversation. Use this before answering questions that "
            "may depend on something the user said before."
        ),
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to search for."}},
            "required": ["query"],
        },
        handler=search_memory,
    )
