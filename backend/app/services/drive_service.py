"""
Google Drive integration: search + read-only file access.

Google Workspace files (Docs, Sheets, Slides) are exported to plain text /
CSV via the Drive export endpoint; regular binary/text files are downloaded
directly. Only read access is requested (drive.readonly scope) — this
integration never creates, modifies, or deletes Drive content.
"""
import asyncio
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

from app.core.exceptions import ExternalServiceError, NotFoundError
from app.core.logging_config import get_logger
from app.services import google_oauth_service

logger = get_logger(__name__)

_GOOGLE_EXPORT_MIME_MAP = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

MAX_READ_CHARS = 20_000


async def _build_drive_client(user_id: str):
    creds = await google_oauth_service.get_valid_credentials(user_id)
    return await asyncio.to_thread(build, "drive", "v3", credentials=creds)


def _handle_http_error(exc: HttpError, context: str) -> None:
    logger.error("Drive API error during %s: %s", context, exc)
    if exc.resp.status == 404:
        raise NotFoundError(f"Drive resource not found during {context}.") from exc
    raise ExternalServiceError(f"Drive API error during {context}: {exc}", error_code="drive_error") from exc


async def search_files(*, user_id: str, query: str, max_results: int = 10) -> list[dict[str, Any]]:
    service = await _build_drive_client(user_id)
    escaped_query = query.replace("'", "\\'")

    def _search():
        return (
            service.files()
            .list(
                q=f"name contains '{escaped_query}' and trashed = false",
                pageSize=min(max(max_results, 1), 50),
                fields="files(id, name, mimeType, modifiedTime, webViewLink, owners)",
            )
            .execute()
        )

    try:
        result = await asyncio.to_thread(_search)
    except HttpError as exc:
        _handle_http_error(exc, "search_files")

    return [
        {
            "file_id": f["id"],
            "name": f["name"],
            "mime_type": f["mimeType"],
            "modified_time": f.get("modifiedTime"),
            "web_view_link": f.get("webViewLink"),
        }
        for f in result.get("files", [])
    ]


def _sync_read_file(service, file_id: str) -> tuple[str, str]:
    metadata = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
    mime_type = metadata["mimeType"]

    if mime_type in _GOOGLE_EXPORT_MIME_MAP:
        request = service.files().export_media(fileId=file_id, mimeType=_GOOGLE_EXPORT_MIME_MAP[mime_type])
    else:
        request = service.files().get_media(fileId=file_id)

    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    raw_bytes = buffer.getvalue()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = f"[Binary file '{metadata['name']}' ({mime_type}) — content is not text-readable.]"

    return metadata["name"], text


async def read_file(*, user_id: str, file_id: str) -> dict[str, Any]:
    service = await _build_drive_client(user_id)
    try:
        name, text = await asyncio.to_thread(_sync_read_file, service, file_id)
    except HttpError as exc:
        _handle_http_error(exc, "read_file")

    truncated = len(text) > MAX_READ_CHARS
    return {
        "file_id": file_id,
        "name": name,
        "content": text[:MAX_READ_CHARS],
        "truncated": truncated,
    }
