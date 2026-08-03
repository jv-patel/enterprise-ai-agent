"""
Security-critical utilities for the Google OAuth flow:

  - `encrypt_token` / `decrypt_token`: Fernet symmetric encryption so access
    and refresh tokens are never stored in plaintext in Supabase.
  - `sign_state` / `verify_state`: HMAC-signed, short-lived `state` values so
    the OAuth callback can be tied back to the initiating user without a
    server-side session, and rejected if tampered with or expired.
"""
import time
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt

from app.config import get_settings
from app.core.exceptions import AppError

STATE_TTL_SECONDS = 600  # 10 minutes to complete the OAuth consent flow


@lru_cache
def _fernet() -> Fernet:
    settings = get_settings()
    if not settings.TOKEN_ENCRYPTION_KEY:
        raise AppError(
            "Token encryption is not configured. Set TOKEN_ENCRYPTION_KEY.",
            error_code="encryption_not_configured",
            status_code=500,
        )
    return Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def encrypt_token(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise AppError("Stored token could not be decrypted.", error_code="token_decryption_failed", status_code=500) from exc


def sign_state(payload: dict[str, Any]) -> str:
    settings = get_settings()
    if not settings.OAUTH_STATE_SECRET:
        raise AppError(
            "OAuth state signing is not configured. Set OAUTH_STATE_SECRET.",
            error_code="oauth_state_not_configured",
            status_code=500,
        )
    to_encode = {**payload, "exp": int(time.time()) + STATE_TTL_SECONDS}
    return jwt.encode(to_encode, settings.OAUTH_STATE_SECRET, algorithm="HS256")


def verify_state(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.OAUTH_STATE_SECRET, algorithms=["HS256"])
    except JWTError as exc:
        raise AppError("Invalid or expired OAuth state.", error_code="invalid_oauth_state", status_code=400) from exc
