from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TaskStatus = Literal["pending", "in_progress", "completed", "cancelled"]
TaskPriority = Literal["low", "medium", "high"]


class TaskCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    priority: TaskPriority = "medium"
    due_at: datetime | None = None
    remind_at: datetime | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_at: datetime | None = None
    remind_at: datetime | None = None


class TaskResponse(BaseModel):
    id: str
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_at: datetime | None
    remind_at: datetime | None
    created_at: datetime
    updated_at: datetime
