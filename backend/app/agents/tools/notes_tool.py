"""Notes management tools, bound to the current user via closures."""
from app.agents.tools.registry import ToolSpec
from app.services import notes_service


def build_notes_tools(*, user_id: str) -> list[ToolSpec]:
    async def create_note(title: str, content: str = "", tags: list[str] | None = None) -> dict:
        note = await notes_service.create_note(user_id=user_id, title=title, content=content, tags=tags)
        return {"note_id": note["id"], "title": note["title"]}

    async def list_notes(tag: str | None = None) -> dict:
        notes = await notes_service.list_notes(user_id, tag=tag)
        return {"notes": [{"id": n["id"], "title": n["title"], "tags": n["tags"]} for n in notes]}

    async def edit_note(note_id: str, title: str | None = None, content: str | None = None) -> dict:
        note = await notes_service.update_note(user_id=user_id, note_id=note_id, title=title, content=content)
        return {"note_id": note["id"], "title": note["title"]}

    async def delete_note(note_id: str) -> dict:
        await notes_service.delete_note(user_id, note_id)
        return {"deleted": True, "note_id": note_id}

    return [
        ToolSpec(
            name="create_note",
            description="Create a new note for the user.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Note title."},
                    "content": {"type": "string", "description": "Note body content."},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags."},
                },
                "required": ["title"],
            },
            handler=create_note,
        ),
        ToolSpec(
            name="list_notes",
            description="List the user's notes, optionally filtered by tag.",
            parameters={
                "type": "object",
                "properties": {"tag": {"type": "string", "description": "Optional tag filter."}},
                "required": [],
            },
            handler=list_notes,
        ),
        ToolSpec(
            name="edit_note",
            description="Edit an existing note's title and/or content.",
            parameters={
                "type": "object",
                "properties": {
                    "note_id": {"type": "string", "description": "ID of the note to edit."},
                    "title": {"type": "string", "description": "New title, if changing."},
                    "content": {"type": "string", "description": "New content, if changing."},
                },
                "required": ["note_id"],
            },
            handler=edit_note,
        ),
        ToolSpec(
            name="delete_note",
            description="Delete a note by its ID.",
            parameters={
                "type": "object",
                "properties": {"note_id": {"type": "string", "description": "ID of the note to delete."}},
                "required": ["note_id"],
            },
            handler=delete_note,
        ),
    ]
