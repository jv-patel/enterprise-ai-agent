"""
Google Gemini integration.

Wraps the `google-generativeai` SDK for:
  - multi-turn chat generation with native function calling (tool use)
  - text embeddings (used by long-term memory search)

All calls are synchronous at the SDK level, so they are run in a thread via
`asyncio.to_thread` to avoid blocking the FastAPI event loop.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any

import google.generativeai as genai

from app.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_CONFIGURED = False


def _ensure_configured() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise ExternalServiceError(
            "Gemini is not configured. Set GEMINI_API_KEY.",
            error_code="gemini_not_configured",
        )
    genai.configure(api_key=settings.GEMINI_API_KEY)
    _CONFIGURED = True


def ensure_configured() -> None:
    """Public entry point for other services (e.g. vision_service) to reuse Gemini configuration."""
    _ensure_configured()


@dataclass
class ToolCallRequest:
    name: str
    args: dict[str, Any]


@dataclass
class GeminiTurnResult:
    text: str | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)


def _history_to_contents(history: list[dict[str, str]]) -> list[dict[str, Any]]:
    """Convert stored chat_messages rows into Gemini `contents` history.

    Gemini uses roles "user" and "model" only (no "assistant"/"system").
    """
    contents: list[dict[str, Any]] = []
    for message in history:
        if message["role"] == "system":
            continue
        role = "model" if message["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [message["content"]]})
    return contents


def _build_function_declarations(tool_specs: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        }
        for spec in tool_specs
    ]


def _extract_turn_result(response: Any) -> GeminiTurnResult:
    result = GeminiTurnResult()
    if not response.candidates:
        return result

    for part in response.candidates[0].content.parts:
        function_call = getattr(part, "function_call", None)
        if function_call is not None and function_call.name:
            result.tool_calls.append(
                ToolCallRequest(name=function_call.name, args=dict(function_call.args))
            )
        text = getattr(part, "text", None)
        if text:
            result.text = (result.text or "") + text

    return result


def _sync_send_message(
    system_instruction: str,
    history: list[dict[str, Any]],
    message_parts: Any,
    tool_specs: list[Any],
    model_name: str,
) -> GeminiTurnResult:
    _ensure_configured()
    tools = [{"function_declarations": _build_function_declarations(tool_specs)}] if tool_specs else None

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=system_instruction,
        tools=tools,
    )
    chat = model.start_chat(history=history)
    try:
        response = chat.send_message(message_parts)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini generation failed")
        raise ExternalServiceError(f"Gemini request failed: {exc}", error_code="gemini_error") from exc

    return _extract_turn_result(response)


async def generate_turn(
    *,
    system_instruction: str,
    history: list[dict[str, str]],
    user_message: str,
    tool_specs: list[Any],
    model_name: str | None = None,
) -> GeminiTurnResult:
    """First turn of a conversation step: send the user's message, optionally with tools."""
    settings = get_settings()
    contents_history = _history_to_contents(history)
    return await asyncio.to_thread(
        _sync_send_message,
        system_instruction,
        contents_history,
        user_message,
        tool_specs,
        model_name or settings.DEFAULT_GEMINI_MODEL,
    )


def _function_call_parts(tool_calls: list[ToolCallRequest]) -> list[Any]:
    return [
        genai.protos.Part(function_call=genai.protos.FunctionCall(name=tc.name, args=tc.args))
        for tc in tool_calls
    ]


def _function_response_parts(tool_results: list[dict[str, Any]]) -> list[Any]:
    return [
        genai.protos.Part(
            function_response=genai.protos.FunctionResponse(
                name=result["name"],
                response={"result": result.get("output"), "error": result.get("error")},
            )
        )
        for result in tool_results
    ]


async def generate_with_tool_results(
    *,
    system_instruction: str,
    history: list[dict[str, str]],
    prior_user_message: str,
    completed_rounds: list[dict[str, Any]],
    latest_tool_calls: list[ToolCallRequest],
    latest_tool_results: list[dict[str, Any]],
    tool_specs: list[Any],
    model_name: str | None = None,
) -> GeminiTurnResult:
    """Continue a conversation turn after tool execution, feeding results back to the model.

    `completed_rounds` holds every earlier (tool_calls, tool_results) pair from
    this same planning loop, so multi-round tool chaining keeps full context.
    Each item is `{"tool_calls": list[ToolCallRequest], "tool_results": list[dict]}`.
    """
    settings = get_settings()
    contents_history = _history_to_contents(history)
    contents_history.append({"role": "user", "parts": [prior_user_message]})

    for round_ in completed_rounds:
        contents_history.append({"role": "model", "parts": _function_call_parts(round_["tool_calls"])})
        contents_history.append({"role": "user", "parts": _function_response_parts(round_["tool_results"])})

    # The latest round's model turn goes into history; its results are sent as the new message.
    contents_history.append({"role": "model", "parts": _function_call_parts(latest_tool_calls)})
    message_parts = _function_response_parts(latest_tool_results)

    return await asyncio.to_thread(
        _sync_send_message,
        system_instruction,
        contents_history,
        message_parts,
        tool_specs,
        model_name or settings.DEFAULT_GEMINI_MODEL,
    )


def _sync_embed(text: str) -> list[float]:
    _ensure_configured()
    try:
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini embedding failed")
        raise ExternalServiceError(f"Gemini embedding failed: {exc}", error_code="gemini_embedding_error") from exc
    return result["embedding"]


async def embed_text(text: str) -> list[float]:
    return await asyncio.to_thread(_sync_embed, text)
