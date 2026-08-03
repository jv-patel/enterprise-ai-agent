from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

NotificationType = Literal["reminder", "agent_run", "system", "google"]


class NotificationResponse(BaseModel):
    id: str
    type: NotificationType
    title: str
    message: str
    read: bool
    metadata: dict[str, Any]
    created_at: datetime


class MarkAllReadResponse(BaseModel):
    marked_read: int
