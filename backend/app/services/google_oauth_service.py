"""
Google OAuth 2.0 flow for Gmail, Calendar, and Drive access.

Uses the standard server-side authorization-code flow (`google-auth-oauthlib`)
with `access_type=offline` + `prompt=consent` to guarantee a refresh token.
Tokens are encrypted (see core/crypto.py) before being persisted to the
`google_credentials` table, and transparently refreshed on read when expired.
"""
import asyncio
from datetime import datetime, timezone

from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import get_settings
from app.core.crypto import decrypt_token, encrypt_token, sign_state, verify_state
from app.core.exceptions import AppError, NotFoundError
from app.core.logging_config import get_logger
from app.database.supabase_client import get_supabase

logger = get_logger(__name__)

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
DRIVE_SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
ALL_SCOPES = GMAIL_SCOPES + CALENDAR_SCOPES + DRIVE_SCOPES


def _require_oauth_configured() -> None:
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise AppError(
            "Google OAuth is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
            error_code="google_oauth_not_configured",
            status_code=500,
        )


def _client_config() -> dict:
    settings = get_settings()
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def _build_flow() -> Flow:
    settings = get_settings()
    return Flow.from_client_config(_client_config(), scopes=ALL_SCOPES, redirect_uri=settings.GOOGLE_REDIRECT_URI)


def build_authorization_url(user_id: str) -> str:
    _require_oauth_configured()
    flow = _build_flow()
    state = sign_state({"user_id": user_id})
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return auth_url


def _sync_exchange_code(code: str) -> Credentials:
    flow = _build_flow()
    flow.fetch_token(code=code)
    return flow.credentials


async def _store_credentials(user_id: str, creds: Credentials) -> None:
    supabase = get_supabase()
    expires_at = creds.expiry.replace(tzinfo=timezone.utc).isoformat() if creds.expiry else None
    supabase.table("google_credentials").upsert(
        {
            "user_id": user_id,
            "access_token": encrypt_token(creds.token),
            "refresh_token": encrypt_token(creds.refresh_token) if creds.refresh_token else "",
            "scopes": list(creds.scopes) if creds.scopes else ALL_SCOPES,
            "expires_at": expires_at,
        },
        on_conflict="user_id",
    ).execute()


async def handle_oauth_callback(*, code: str, state: str) -> str:
    """Exchanges the auth code for tokens, stores them, returns the user_id from `state`."""
    _require_oauth_configured()
    payload = verify_state(state)
    user_id = payload["user_id"]

    creds = await asyncio.to_thread(_sync_exchange_code, code)
    if not creds.refresh_token:
        logger.warning(
            "No refresh token returned for user %s (already granted consent previously?)", user_id
        )
    await _store_credentials(user_id, creds)
    return user_id


async def get_connection_status(user_id: str) -> dict:
    supabase = get_supabase()
    response = (
        supabase.table("google_credentials")
        .select("scopes, expires_at, updated_at")
        .eq("user_id", user_id)
        .limit(1)
        .execute()
    )
    if not response.data:
        return {"connected": False, "scopes": [], "expires_at": None}
    row = response.data[0]
    return {"connected": True, "scopes": row["scopes"], "expires_at": row["expires_at"]}


async def disconnect(user_id: str) -> None:
    supabase = get_supabase()
    supabase.table("google_credentials").delete().eq("user_id", user_id).execute()


def _sync_refresh(creds: Credentials) -> Credentials:
    creds.refresh(GoogleAuthRequest())
    return creds


async def get_valid_credentials(user_id: str) -> Credentials:
    """Loads stored credentials, transparently refreshing (and re-persisting) if expired."""
    supabase = get_supabase()
    response = (
        supabase.table("google_credentials").select("*").eq("user_id", user_id).limit(1).execute()
    )
    if not response.data:
        raise NotFoundError("Google account is not connected. Complete the Google OAuth flow first.")

    row = response.data[0]
    settings = get_settings()
    creds = Credentials(
        token=decrypt_token(row["access_token"]),
        refresh_token=decrypt_token(row["refresh_token"]) if row["refresh_token"] else None,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=row["scopes"],
    )

    expires_at = datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None
    is_expired = expires_at is not None and expires_at <= datetime.now(timezone.utc)

    if is_expired:
        if not creds.refresh_token:
            raise AppError(
                "Google session expired and no refresh token is available. Please reconnect Google.",
                error_code="google_reauth_required",
                status_code=401,
            )
        creds = await asyncio.to_thread(_sync_refresh, creds)
        await _store_credentials(user_id, creds)

    return creds
