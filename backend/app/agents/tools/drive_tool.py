"""Google Drive agent tools, bound to the current user via closures."""
from app.agents.tools.registry import ToolSpec
from app.services import drive_service


def build_drive_tools(*, user_id: str) -> list[ToolSpec]:
    async def search_drive_files(query: str, max_results: int = 10) -> dict:
        files = await drive_service.search_files(user_id=user_id, query=query, max_results=max_results)
        return {"files": files}

    async def read_drive_file(file_id: str) -> dict:
        return await drive_service.read_file(user_id=user_id, file_id=file_id)

    return [
        ToolSpec(
            name="search_drive_files",
            description="Search the user's Google Drive for files by name.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Text to search for in file names."},
                    "max_results": {"type": "integer", "description": "Number of results to return (1-50). Defaults to 10."},
                },
                "required": ["query"],
            },
            handler=search_drive_files,
        ),
        ToolSpec(
            name="read_drive_file",
            description=(
                "Read the text content of a Google Drive file by its file ID. Google Docs/Sheets/Slides "
                "are automatically converted to text/CSV."
            ),
            parameters={
                "type": "object",
                "properties": {"file_id": {"type": "string", "description": "Google Drive file ID."}},
                "required": ["file_id"],
            },
            handler=read_drive_file,
        ),
    ]
