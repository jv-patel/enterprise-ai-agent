"""Shared state passed between LangGraph nodes for a single agent run."""
from typing import Any, TypedDict

from app.agents.tools.registry import ToolSpec
from app.services.gemini_service import ChatSession, ToolCallRequest


class AgentState(TypedDict, total=False):
    # Identity / scope
    user_id: str
    chat_id: str
    run_id: str
    agent_name: str
    system_prompt: str

    # Input
    user_message: str

    # Context loaded once at the start of the run
    conversation_history: list[dict[str, str]]
    long_term_context: list[str]
    tool_specs: list[ToolSpec]

    # Working turn state
    chat_session: ChatSession
    pending_tool_calls: list[ToolCallRequest]
    last_tool_results: list[dict[str, Any]]
    tool_rounds: list[dict[str, Any]]
    step_index: int
    plan_iterations: int
    retries: dict[str, int]
    max_retries: int
    max_plan_iterations: int

    # Output
    final_answer: str | None
    error: str | None
