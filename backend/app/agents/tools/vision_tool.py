"""Vision agent tools, bound to the current user via closures. Operate on
previously uploaded images (see file_tool.list_uploaded_files to discover file IDs)."""
from app.agents.tools.registry import ToolSpec
from app.core.exceptions import ValidationAppError
from app.services import file_service, storage_service, vision_service


async def _load_image(user_id: str, file_id: str) -> tuple[bytes, str]:
    file_row = await file_service.get_uploaded_file(user_id, file_id)
    if file_row["file_type"] not in file_service.IMAGE_TYPES:
        raise ValidationAppError("That file is not an image.", error_code="not_an_image")
    content = await storage_service.download_file(file_row["storage_path"])
    mime_type = file_service.CONTENT_TYPE_MAP.get(file_row["file_type"], "application/octet-stream")
    return content, mime_type


def build_vision_tools(*, user_id: str) -> list[ToolSpec]:
    async def analyze_uploaded_image(file_id: str, prompt: str | None = None) -> dict:
        content, mime_type = await _load_image(user_id, file_id)
        result = await vision_service.analyze_image(image_bytes=content, mime_type=mime_type, prompt=prompt)
        return {"file_id": file_id, "analysis": result}

    async def ocr_uploaded_image(file_id: str) -> dict:
        content, mime_type = await _load_image(user_id, file_id)
        result = await vision_service.extract_text_ocr(image_bytes=content, mime_type=mime_type)
        return {"file_id": file_id, "extracted_text": result}

    return [
        ToolSpec(
            name="analyze_image",
            description=(
                "Analyze a previously uploaded image (photo, screenshot, or chart) using Gemini Vision. "
                "Optionally focus the analysis with a specific prompt/question."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_id": {"type": "string", "description": "ID of the uploaded image file."},
                    "prompt": {"type": "string", "description": "Optional specific question or focus for the analysis."},
                },
                "required": ["file_id"],
            },
            handler=analyze_uploaded_image,
        ),
        ToolSpec(
            name="ocr_image",
            description="Extract all readable text from a previously uploaded image via OCR.",
            parameters={
                "type": "object",
                "properties": {"file_id": {"type": "string", "description": "ID of the uploaded image file."}},
                "required": ["file_id"],
            },
            handler=ocr_uploaded_image,
        ),
    ]
