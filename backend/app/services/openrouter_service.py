"""
OpenRouter integration — fallback / alternate LLM provider.

OpenRouter exposes an OpenAI-compatible `/chat/completions` endpoint, used
here as a plain-text fallback path (no native tool calling) for when a user
prefers a non-Gemini model or Gemini is unavailable.
"""
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
async def _post_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    if not settings.OPENROUTER_API_KEY:
        raise ExternalServiceError(
            "OpenRouter is not configured. Set OPENROUTER_API_KEY.",
            error_code="openrouter_not_configured",
        )

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://enterprise-ai-agent.app",
        "X-Title": "Enterprise AI Personal Agent",
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.OPENROUTER_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
    if response.status_code >= 400:
        logger.error("OpenRouter error %s: %s", response.status_code, response.text)
        raise ExternalServiceError(
            f"OpenRouter request failed with status {response.status_code}",
            error_code="openrouter_error",
        )
    return response.json()


async def generate_text(
    *,
    system_instruction: str,
    history: list[dict[str, str]],
    user_message: str,
    model_name: str | None = None,
) -> str:
    messages = [{"role": "system", "content": system_instruction}]
    for message in history:
        messages.append({"role": message["role"], "content": message["content"]})
    messages.append({"role": "user", "content": user_message})

    settings = get_settings()
    payload = {
        "model": model_name or DEFAULT_OPENROUTER_MODEL,
        "messages": messages,
    }
    data = await _post_chat_completion(payload)
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError) as exc:
        raise ExternalServiceError("Unexpected OpenRouter response shape", error_code="openrouter_error") from exc
