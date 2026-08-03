"""
Central application configuration.

All configuration is sourced from environment variables (see .env.example).
No secrets or credentials are ever hardcoded here.
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    APP_NAME: str = "Enterprise AI Personal Agent"
    ENVIRONMENT: str = Field(default="development")
    API_V1_PREFIX: str = "/api/v1"
    LOG_LEVEL: str = "INFO"

    # --- CORS ---
    FRONTEND_ORIGINS: str = "http://localhost:3000"

    # --- Supabase / Database ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""
    DATABASE_URL: str = ""

    # --- Firebase Auth ---
    FIREBASE_PROJECT_ID: str = ""
    FIREBASE_SERVICE_ACCOUNT_JSON: str = ""

    # --- Google OAuth (Gmail / Calendar / Drive) ---
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/google/oauth/callback"
    GOOGLE_POST_AUTH_REDIRECT_URL: str = "http://localhost:3000/dashboard/settings?google=connected"
    GOOGLE_POST_AUTH_ERROR_REDIRECT_URL: str = "http://localhost:3000/dashboard/settings?google=error"

    # --- Token security ---
    # Fernet key (32 url-safe base64 bytes) used to encrypt stored OAuth tokens at rest.
    # Generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    TOKEN_ENCRYPTION_KEY: str = ""
    # HMAC secret used to sign the OAuth `state` parameter (CSRF protection / user binding).
    OAUTH_STATE_SECRET: str = ""

    # --- AI Providers ---
    GEMINI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    DEFAULT_GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- Utilities (tools, future phases) ---
    WEATHER_API_KEY: str = ""
    WEB_SEARCH_API_KEY: str = ""

    # --- Voice AI (Google Cloud Speech-to-Text / Text-to-Speech) ---
    # Auth for these clients is via Application Default Credentials
    # (GOOGLE_APPLICATION_CREDENTIALS env var pointing at a service account
    # JSON key) — see docs/GOOGLE_CLOUD_SETUP.md.
    GOOGLE_TTS_VOICE_NAME: str = "en-US-Neural2-C"
    GOOGLE_TTS_LANGUAGE_CODE: str = "en-US"
    GOOGLE_STT_LANGUAGE_CODE: str = "en-US"

    # --- File / Storage ---
    SUPABASE_STORAGE_BUCKET: str = "user-uploads"
    MAX_UPLOAD_BYTES: int = 20 * 1024 * 1024

    # --- Security ---
    JWT_ALGORITHM: str = "RS256"
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def frontend_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.FRONTEND_ORIGINS.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
