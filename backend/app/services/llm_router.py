"""
Provider-agnostic text generation.

Tool-calling turns in the agent graph always go through `gemini_service`
directly, since Gemini's native function-calling protocol is what the tool
executor is built against. This router is for plain-text generation (e.g.
summaries, titles) where the user's configured provider preference should
be honored.
"""
from app.core.logging_config import get_logger
from app.services import gemini_service, openrouter_service

logger = get_logger(__name__)


async def generate_reply(
    *,
    provider: str,
    system_instruction: str,
    history: list[dict[str, str]],
    user_message: str,
    model_name: str | None = None,
) -> str:
    if provider == "openrouter":
        return await openrouter_service.generate_text(
            system_instruction=system_instruction,
            history=history,
            user_message=user_message,
            model_name=model_name,
        )

    result = await gemini_service.generate_turn(
        system_instruction=system_instruction,
        history=history,
        user_message=user_message,
        tool_specs=[],
        model_name=model_name,
    )
    return result.text or ""
