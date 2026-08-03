from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentRunRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    chat_id: str | None = None
    agent_name: str | None = Field(
        default=None, description="Explicit specialist agent key to use instead of Coordinator Agent auto-routing."
    )


class AgentRunResponse(BaseModel):
    run_id: str
    chat_id: str
    answer: str
    status: str
    agent_name: str


class AgentDefinitionResponse(BaseModel):
    key: str
    display_name: str
    description: str


class AgentLogEntry(BaseModel):
    id: str
    run_id: str
    step_index: int
    agent_name: str
    action_type: str
    detail: dict[str, Any]
    created_at: datetime


class AgentRunSummary(BaseModel):
    id: str
    chat_id: str | None
    agent_name: str
    goal: str
    status: str
    started_at: datetime
    completed_at: datetime | None
