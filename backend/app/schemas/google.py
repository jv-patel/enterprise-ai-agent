from datetime import datetime

from pydantic import BaseModel


class GoogleAuthUrlResponse(BaseModel):
    authorization_url: str


class GoogleConnectionStatus(BaseModel):
    connected: bool
    scopes: list[str]
    expires_at: datetime | None
