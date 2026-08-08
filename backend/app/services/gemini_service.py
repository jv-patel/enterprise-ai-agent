"""
Google Gemini integration.

Uses the `google-genai` SDK (Google's current, actively maintained client —
the older `google-generativeai` package is being phased out). A stateful
chat session is created per agent run and reused across every planning
round: the SDK's own history handling automatically preserves "thought
signatures" that Gemini 3.x models require for multi-turn function calling.
Manually rebuilding conversation history (as the legacy SDK required) drops
those signatures and causes 400 errors on the second tool-calling round —
this design avoids that entirely.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Any

from google import genai
from google.genai import types

from app.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_CLIENT: genai.Client | None = None


def _ensure_client() -> genai.Client:
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    settings = get_settings()
    if not settings.GEMINI_API_KEY:
        raise ExternalServiceError(
            "Gemini is not configured. Set GEMINI_API_KEY.",
            error_code="gemini_not_configured",
        )
    _CLIENT = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _CLIENT


def ensure_configured() -> None:
    """Public entry point for other services (e.g. vision_service) to reuse Gemini configuration."""
    _ensure_client()


def get_client() -> genai.Client:
    """Public accessor for the shared Gemini client (used by vision_service for one-shot multimodal calls)."""
    return _ensure_client()


@dataclass
class ToolCallRequest:
    name: str
    args: dict[str, Any]


@dataclass
class GeminiTurnResult:
    text: str | None = None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)


def _history_to_contents(history: list[dict[str, str]]) -> list[types.Content]:
    """Convert stored chat_messages rows into google-genai `Content` history.

    Gemini uses roles "user" and "model" only (no "assistant"/"system").
    """
    contents: list[types.Content] = []
    for message in history:
        if message["role"] == "system":
            continue
        role = "model" if message["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=message["content"])]))
    return contents


def _build_tools(tool_specs: list[Any]) -> list[types.Tool] | None:
    if not tool_specs:
        return None
    declarations = [
        types.FunctionDeclaration(name=spec.name, description=spec.description, parameters=spec.parameters)
        for spec in tool_specs
    ]
    return [types.Tool(function_declarations=declarations)]


def _extract_turn_result(response: Any) -> GeminiTurnResult:
    result = GeminiTurnResult()
    candidates = getattr(response, "candidates", None)
    if not candidates:
        return result

    parts = candidates[0].content.parts or []
    for part in parts:
        function_call = getattr(part, "function_call", None)
        if function_call is not None and function_call.name:
            result.tool_calls.append(
                ToolCallRequest(name=function_call.name, args=dict(function_call.args or {}))
            )
        text = getattr(part, "text", None)
        if text:
            result.text = (result.text or "") + text

    return result


class ChatSession:
    """Wraps a google-genai chat session; offloads the SDK's synchronous
    calls to a thread so the FastAPI event loop is never blocked."""

    def __init__(self, chat: Any) -> None:
        self._chat = chat

    def _sync_send(self, message: Any) -> Any:
        try:
            return self._chat.send_message(message)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Gemini generation failed")
            raise ExternalServiceError(f"Gemini request failed: {exc}", error_code="gemini_error") from exc

    async def send(self, message: Any) -> GeminiTurnResult:
        response = await asyncio.to_thread(self._sync_send, message)
        return _extract_turn_result(response)


def create_chat_session(
    *,
    system_instruction: str,
    history: list[dict[str, str]],
    tool_specs: list[Any],
    model_name: str | None = None,
) -> ChatSession:
    client = _ensure_client()
    settings = get_settings()
    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=_build_tools(tool_specs),
    )
    chat = client.chats.create(
        model=model_name or settings.DEFAULT_GEMINI_MODEL,
        config=config,
        history=_history_to_contents(history),
    )
    return ChatSession(chat)


def build_tool_result_message(tool_results: list[dict[str, Any]]) -> list[types.Part]:
    """Builds the function-response parts sent back to a live chat session
    after tool execution. The SDK preserves thought signatures automatically
    as long as the same ChatSession object keeps being used."""
    return [
        types.Part.from_function_response(
            name=result["name"],
            response={"result": result.get("output"), "error": result.get("error")},
        )
        for result in tool_results
    ]


async def generate_turn(
    *,
    system_instruction: str,
    history: list[dict[str, str]],
    user_message: str,
    tool_specs: list[Any],
    model_name: str | None = None,
) -> GeminiTurnResult:
    """One-shot generation (no ongoing multi-round tool use) — used for
    routing, summarization, Q&A, and other single-turn tasks."""
    session = create_chat_session(
        system_instruction=system_instruction, history=history, tool_specs=tool_specs, model_name=model_name
    )
    return await session.send(user_message)


def _sync_embed(text: str) -> list[float]:
    client = _ensure_client()
    try:
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=768),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini embedding failed")
        raise ExternalServiceError(f"Gemini embedding failed: {exc}", error_code="gemini_embedding_error") from exc
    return list(result.embeddings[0].values)


async def embed_text(text: str) -> list[float]:
    return await asyncio.to_thread(_sync_embed, text)
