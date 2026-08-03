"""
Supabase client singleton.

All database access in this project goes through Supabase's Python client
using the service-role key on the backend (never exposed to the frontend,
which uses its own anon key + Firebase-issued JWTs).
"""
from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings
from app.core.exceptions import AppError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        raise AppError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.",
            error_code="supabase_not_configured",
            status_code=500,
        )
    logger.info("Initializing Supabase client for project: %s", settings.SUPABASE_URL)
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
