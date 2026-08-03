"""
Orchestrates the full lifecycle of an uploaded file: storage upload, text
extraction (documents) or pass-through (images, handled by vision_service),
persistence to `uploaded_files`, summarization, and grounded Q&A.
"""
import asyncio
from typing import Any

from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase
from app.services import file_extraction_service, gemini_service, storage_service

logger = get_logger(__name__)

IMAGE_TYPES = {"png", "jpg", "jpeg", "webp", "gif"}
DOCUMENT_TYPES = file_extraction_service.SUPPORTED_TYPES
SUPPORTED_UPLOAD_TYPES = DOCUMENT_TYPES | IMAGE_TYPES

CONTENT_TYPE_MAP = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "csv": "text/csv",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
}

MAX_SUMMARY_CONTEXT_CHARS = 12_000
MAX_READ_CHARS = 6_000


async def upload_and_process_file(
    *, user_id: str, chat_id: str | None, file_name: str, content: bytes, file_type: str
) -> dict[str, Any]:
    normalized_type = file_type.lower().lstrip(".")
    if normalized_type not in SUPPORTED_UPLOAD_TYPES:
        raise ValidationAppError(
            f"Unsupported file type: {normalized_type}. Supported: {sorted(SUPPORTED_UPLOAD_TYPES)}",
            error_code="unsupported_file_type",
        )

    content_type = CONTENT_TYPE_MAP.get(normalized_type, "application/octet-stream")
    storage_path = await storage_service.upload_file(
        user_id=user_id, file_name=file_name, content=content, content_type=content_type
    )

    extracted_text: str | None = None
    if normalized_type in DOCUMENT_TYPES:
        extracted_text = await asyncio.to_thread(
            file_extraction_service.extract_text, content=content, file_type=normalized_type
        )

    supabase = get_supabase()
    response = (
        supabase.table("uploaded_files")
        .insert(
            {
                "user_id": user_id,
                "chat_id": chat_id,
                "file_name": file_name,
                "file_type": normalized_type,
                "storage_path": storage_path,
                "extracted_text": extracted_text,
            }
        )
        .execute()
    )
    return response.data[0]


async def get_uploaded_file(user_id: str, file_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    response = (
        supabase.table("uploaded_files").select("*").eq("id", file_id).eq("user_id", user_id).limit(1).execute()
    )
    if not response.data:
        raise NotFoundError(f"Uploaded file {file_id} not found.")
    return response.data[0]


async def list_uploaded_files(user_id: str, chat_id: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    supabase = get_supabase()
    query = (
        supabase.table("uploaded_files")
        .select("id, file_name, file_type, created_at, summary")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if chat_id:
        query = query.eq("chat_id", chat_id)
    return query.execute().data


async def read_file_content(user_id: str, file_id: str) -> dict[str, Any]:
    file_row = await get_uploaded_file(user_id, file_id)
    text = file_row.get("extracted_text") or ""
    if file_row["file_type"] in IMAGE_TYPES:
        raise ValidationAppError(
            "This is an image file — use the vision endpoints (/vision/analyze, /vision/ocr) to read it.",
            error_code="not_a_document",
        )
    return {
        "file_id": file_id,
        "file_name": file_row["file_name"],
        "content": text[:MAX_READ_CHARS],
        "truncated": len(text) > MAX_READ_CHARS,
    }


async def summarize_file(user_id: str, file_id: str) -> dict[str, Any]:
    file_row = await get_uploaded_file(user_id, file_id)
    text = file_row.get("extracted_text") or ""
    if not text.strip():
        raise ValidationAppError("This file has no extractable text content to summarize.", error_code="empty_file_content")

    prompt = (
        "Summarize the following document clearly and concisely. Cover its key points, "
        "structure, and any important data, figures, or conclusions.\n\n---\n\n" + text[:MAX_SUMMARY_CONTEXT_CHARS]
    )
    result = await gemini_service.generate_turn(
        system_instruction="You are a precise, factual document summarization assistant.",
        history=[],
        user_message=prompt,
        tool_specs=[],
    )
    summary = result.text or "Unable to generate a summary for this document."

    supabase = get_supabase()
    supabase.table("uploaded_files").update({"summary": summary}).eq("id", file_id).execute()
    return {"file_id": file_id, "summary": summary}


async def ask_question_about_file(user_id: str, file_id: str, question: str) -> dict[str, Any]:
    file_row = await get_uploaded_file(user_id, file_id)
    text = file_row.get("extracted_text") or ""
    if not text.strip():
        raise ValidationAppError("This file has no extractable text content.", error_code="empty_file_content")

    prompt = (
        "Using ONLY the document content below, answer the question as accurately as possible. "
        "If the answer isn't contained in the document, say so explicitly.\n\n"
        f"Document:\n{text[:MAX_SUMMARY_CONTEXT_CHARS]}\n\nQuestion: {question}"
    )
    result = await gemini_service.generate_turn(
        system_instruction="You are a precise question-answering assistant grounded strictly in the provided document.",
        history=[],
        user_message=prompt,
        tool_specs=[],
    )
    return {
        "file_id": file_id,
        "question": question,
        "answer": result.text or "I couldn't find an answer to that in the document.",
    }
