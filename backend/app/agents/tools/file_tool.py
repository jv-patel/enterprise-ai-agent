"""File intelligence agent tools, bound to the current user via closures."""
from app.agents.tools.registry import ToolSpec
from app.services import file_service


def build_file_tools(*, user_id: str) -> list[ToolSpec]:
    async def list_uploaded_files() -> dict:
        files = await file_service.list_uploaded_files(user_id)
        return {
            "files": [
                {"id": f["id"], "file_name": f["file_name"], "file_type": f["file_type"], "has_summary": bool(f["summary"])}
                for f in files
            ]
        }

    async def read_file(file_id: str) -> dict:
        return await file_service.read_file_content(user_id, file_id)

    async def summarize_file(file_id: str) -> dict:
        return await file_service.summarize_file(user_id, file_id)

    async def ask_question_about_file(file_id: str, question: str) -> dict:
        return await file_service.ask_question_about_file(user_id, file_id, question)

    return [
        ToolSpec(
            name="list_uploaded_files",
            description="List the files (documents and images) the user has previously uploaded.",
            parameters={"type": "object", "properties": {}, "required": []},
            handler=list_uploaded_files,
        ),
        ToolSpec(
            name="read_file",
            description="Read the extracted text content of a previously uploaded document by file ID.",
            parameters={
                "type": "object",
                "properties": {"file_id": {"type": "string", "description": "ID of the uploaded file."}},
                "required": ["file_id"],
            },
            handler=read_file,
        ),
        ToolSpec(
            name="summarize_file",
            description="Generate and save a summary of a previously uploaded document by file ID.",
            parameters={
                "type": "object",
                "properties": {"file_id": {"type": "string", "description": "ID of the uploaded file."}},
                "required": ["file_id"],
            },
            handler=summarize_file,
        ),
        ToolSpec(
            name="ask_question_about_file",
            description="Answer a question grounded strictly in the content of a previously uploaded document.",
            parameters={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded file."},
                    "question": {"type": "string", "description": "The question to answer using the document."},
                },
                "required": ["file_id", "question"],
            },
            handler=ask_question_about_file,
        ),
    ]
