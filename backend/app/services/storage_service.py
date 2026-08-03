"""
Supabase Storage integration for uploaded files (documents, images).

Requires a bucket named per `settings.SUPABASE_STORAGE_BUCKET` (default
"user-uploads") to already exist in the Supabase project — create it once
via Dashboard → Storage → New Bucket (private, not public) or the Supabase
CLI. Objects are namespaced per-user (`{user_id}/{uuid}_{filename}`).
"""
import asyncio
import uuid

from app.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase

logger = get_logger(__name__)


def _sync_upload(bucket: str, path: str, content: bytes, content_type: str) -> None:
    supabase = get_supabase()
    supabase.storage.from_(bucket).upload(
        path, content, {"content-type": content_type, "upsert": "true"}
    )


def _sync_download(bucket: str, path: str) -> bytes:
    supabase = get_supabase()
    return supabase.storage.from_(bucket).download(path)


async def upload_file(*, user_id: str, file_name: str, content: bytes, content_type: str) -> str:
    settings = get_settings()
    safe_name = file_name.replace("/", "_").replace("\\", "_")
    object_path = f"{user_id}/{uuid.uuid4().hex}_{safe_name}"
    try:
        await asyncio.to_thread(_sync_upload, settings.SUPABASE_STORAGE_BUCKET, object_path, content, content_type)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Supabase storage upload failed")
        raise ExternalServiceError(f"File upload failed: {exc}", error_code="storage_upload_error") from exc
    return object_path


async def download_file(storage_path: str) -> bytes:
    settings = get_settings()
    try:
        return await asyncio.to_thread(_sync_download, settings.SUPABASE_STORAGE_BUCKET, storage_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Supabase storage download failed")
        raise ExternalServiceError(f"File download failed: {exc}", error_code="storage_download_error") from exc
