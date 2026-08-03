from datetime import datetime

from pydantic import BaseModel


class UsageAnalytics(BaseModel):
    total_chats: int
    total_messages: int
    total_notes: int
    total_tasks: int
    total_files_uploaded: int
    total_agent_runs: int


class AgentUsageStat(BaseModel):
    agent_name: str
    run_count: int
    completed_count: int
    failed_count: int


class ToolUsageStat(BaseModel):
    tool_name: str
    usage_count: int


class AiStatistics(BaseModel):
    total_runs: int
    completed_runs: int
    failed_runs: int
    success_rate_percent: float
    runs_by_agent: list[AgentUsageStat]
    top_tools: list[ToolUsageStat]


class ActivityLogEntry(BaseModel):
    id: str
    run_id: str
    agent_name: str
    tool: str | None
    success: bool
    created_at: datetime
