"""
Tool registry.

Each tool is described by a `ToolSpec`: a Gemini-compatible function
declaration (`name`, `description`, JSON-schema `parameters`) plus an async
`handler` bound to the current user/chat via closures. `build_tool_specs`
assembles the full toolset the agent graph can call for a given run.
"""
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Awaitable[Any]]


def build_tool_specs(*, user_id: str, chat_id: str | None) -> list[ToolSpec]:
    from app.agents.tools.calculator_tool import build_calculator_tool
    from app.agents.tools.calendar_tool import build_calendar_tools
    from app.agents.tools.datetime_tool import build_current_date_tool, build_current_time_tool
    from app.agents.tools.drive_tool import build_drive_tools
    from app.agents.tools.file_tool import build_file_tools
    from app.agents.tools.gmail_tool import build_gmail_tools
    from app.agents.tools.memory_tool import build_save_memory_tool, build_search_memory_tool
    from app.agents.tools.notes_tool import build_notes_tools
    from app.agents.tools.task_tool import build_task_tools
    from app.agents.tools.vision_tool import build_vision_tools
    from app.agents.tools.weather_tool import build_weather_tool
    from app.agents.tools.web_search_tool import build_web_search_tool

    tools: list[ToolSpec] = [
        build_calculator_tool(),
        build_current_time_tool(),
        build_current_date_tool(),
        build_weather_tool(),
        build_web_search_tool(),
        build_save_memory_tool(user_id=user_id, chat_id=chat_id),
        build_search_memory_tool(user_id=user_id),
        *build_notes_tools(user_id=user_id),
        *build_task_tools(user_id=user_id),
        *build_gmail_tools(user_id=user_id),
        *build_calendar_tools(user_id=user_id),
        *build_drive_tools(user_id=user_id),
        *build_file_tools(user_id=user_id),
        *build_vision_tools(user_id=user_id),
    ]
    return tools


def get_tool_by_name(tool_specs: list[ToolSpec], name: str) -> ToolSpec | None:
    for spec in tool_specs:
        if spec.name == name:
            return spec
    return None
