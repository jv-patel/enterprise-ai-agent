from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

Theme = Literal["light", "dark", "system"]
Provider = Literal["gemini", "openrouter"]


class UserBootstrapRequest(BaseModel):
    email: EmailStr
    display_name: str | None = Field(default=None, max_length=200)


class UserProfileResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    photo_url: str | None
    auth_provider: str
    created_at: datetime


class UserProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, max_length=200)
    photo_url: str | None = None


class UserSettingsResponse(BaseModel):
    user_id: str
    theme: Theme
    preferred_ai_model: str
    preferred_provider: Provider
    voice_enabled: bool
    notification_prefs: dict[str, Any]


class UserSettingsUpdateRequest(BaseModel):
    theme: Theme | None = None
    preferred_ai_model: str | None = None
    preferred_provider: Provider | None = None
    voice_enabled: bool | None = None
    notification_prefs: dict[str, Any] | None = None
