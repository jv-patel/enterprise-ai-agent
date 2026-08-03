"""
Multi-agent definitions.

Each specialized agent reuses the same underlying LangGraph plan/act engine
(`agents/graph.py`) — what differs per agent is its system prompt and which
tools from the full registry it's allowed to call. The Coordinator Agent
(`agents/router.py` + `agents/coordinator.py`) decides which of these
handles a given user message.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDefinition:
    key: str
    display_name: str
    description: str
    tool_names: frozenset[str] | None  # None = full tool registry (Assistant Agent)
    system_prompt: str


ASSISTANT_AGENT = AgentDefinition(
    key="assistant_agent",
    display_name="Assistant Agent",
    description="General-purpose assistant for anything that doesn't clearly belong to a specialist agent.",
    tool_names=None,
    system_prompt=(
        "You are the general-purpose Assistant Agent for the Enterprise AI Personal Agent. "
        "You have access to the full tool registry. Handle the user's request directly and "
        "efficiently, using tools whenever they improve accuracy."
    ),
)

EMAIL_AGENT = AgentDefinition(
    key="email_agent",
    display_name="Email Agent",
    description="Sending, reading, replying to, and deleting Gmail messages.",
    tool_names=frozenset({"send_email", "read_inbox", "reply_email", "delete_email"}),
    system_prompt=(
        "You are the Email Agent, a specialist in managing the user's Gmail. Handle sending, "
        "reading, replying to, and deleting emails precisely and safely. Always confirm the "
        "key details (recipient, subject) are correct before sending. Be concise in email bodies "
        "unless the user asks for something longer."
    ),
)

CALENDAR_AGENT = AgentDefinition(
    key="calendar_agent",
    display_name="Calendar Agent",
    description="Creating, updating, deleting Google Calendar events and listing upcoming meetings.",
    tool_names=frozenset(
        {"create_calendar_event", "update_calendar_event", "delete_calendar_event", "list_upcoming_meetings", "current_date", "current_time"}
    ),
    system_prompt=(
        "You are the Calendar Agent, a specialist in managing the user's Google Calendar. "
        "Resolve relative dates/times (e.g. 'tomorrow at 3pm') using the current_date/current_time "
        "tools before creating or updating events. Confirm event details before finalizing."
    ),
)

RESEARCH_AGENT = AgentDefinition(
    key="research_agent",
    display_name="Research Agent",
    description="Answering questions that require live web search or recalling prior conversation context.",
    tool_names=frozenset({"web_search", "search_memory", "current_date", "current_time"}),
    system_prompt=(
        "You are the Research Agent. Use web_search for anything requiring current or external "
        "information, and search_memory for anything that may depend on prior conversations. "
        "Synthesize findings into a clear, well-organized answer and note where information came from."
    ),
)

VISION_AGENT = AgentDefinition(
    key="vision_agent",
    display_name="Vision Agent",
    description="Analyzing, describing, and extracting text (OCR) from previously uploaded images.",
    tool_names=frozenset({"analyze_image", "ocr_image", "list_uploaded_files"}),
    system_prompt=(
        "You are the Vision Agent, a specialist in image understanding. Use list_uploaded_files "
        "if you need to find the right file_id, then analyze_image or ocr_image as appropriate. "
        "Describe visual content precisely and factually."
    ),
)

NOTES_AGENT = AgentDefinition(
    key="notes_agent",
    display_name="Notes Agent",
    description="Creating, editing, listing, and deleting the user's notes.",
    tool_names=frozenset({"create_note", "list_notes", "edit_note", "delete_note"}),
    system_prompt=(
        "You are the Notes Agent, a specialist in managing the user's notes. Keep note titles "
        "short and content well-organized. Confirm destructive actions (deletes) succeeded."
    ),
)

TASK_AGENT = AgentDefinition(
    key="task_agent",
    display_name="Task Agent",
    description="Creating, updating, deleting tasks, and managing reminders.",
    tool_names=frozenset({"create_task", "list_tasks", "update_task", "delete_task", "list_reminders", "current_date", "current_time"}),
    system_prompt=(
        "You are the Task Agent, a specialist in managing the user's tasks and reminders. "
        "Resolve relative dates using current_date/current_time before setting due_at/remind_at. "
        "Confirm priority and due dates are reasonable given what the user asked."
    ),
)

SPECIALIZED_AGENTS: dict[str, AgentDefinition] = {
    agent.key: agent
    for agent in [ASSISTANT_AGENT, EMAIL_AGENT, CALENDAR_AGENT, RESEARCH_AGENT, VISION_AGENT, NOTES_AGENT, TASK_AGENT]
}


def get_agent_definition(key: str) -> AgentDefinition:
    return SPECIALIZED_AGENTS.get(key, ASSISTANT_AGENT)


def list_agent_definitions() -> list[AgentDefinition]:
    return list(SPECIALIZED_AGENTS.values())
