"""
Gemini Vision integration for image understanding, OCR, screenshot analysis,
and chart/graph analysis. All four features share one underlying multimodal
call (`_sync_generate`) with task-specific prompts.
"""
import asyncio

import google.generativeai as genai

from app.config import get_settings
from app.core.exceptions import ExternalServiceError
from app.core.logging_config import get_logger
from app.services.gemini_service import ensure_configured

logger = get_logger(__name__)

_DEFAULT_DESCRIBE_PROMPT = "Describe this image in detail, including notable objects, text, people, and context."
_OCR_PROMPT = (
    "Extract all readable text from this image exactly as it appears, preserving line "
    "breaks and layout order as closely as possible. Return only the extracted text, no "
    "commentary or explanation."
)
_SCREENSHOT_PROMPT = (
    "This is a screenshot of a software UI. Describe the layout, key elements (buttons, "
    "menus, fields), any visible text or error messages, and what the screen appears to "
    "be for."
)
_CHART_PROMPT = (
    "This image contains a chart or graph. Identify the chart type, describe the axes "
    "and legend, and summarize the key trends, values, and insights it shows."
)


def _sync_generate(prompt: str, image_bytes: bytes, mime_type: str, model_name: str) -> str:
    ensure_configured()
    model = genai.GenerativeModel(model_name)
    try:
        response = model.generate_content([prompt, {"mime_type": mime_type, "data": image_bytes}])
    except Exception as exc:  # noqa: BLE001
        logger.exception("Gemini vision request failed")
        raise ExternalServiceError(f"Gemini vision request failed: {exc}", error_code="gemini_vision_error") from exc
    return response.text or ""


async def analyze_image(
    *, image_bytes: bytes, mime_type: str, prompt: str | None = None, model_name: str | None = None
) -> str:
    settings = get_settings()
    final_prompt = prompt or _DEFAULT_DESCRIBE_PROMPT
    return await asyncio.to_thread(
        _sync_generate, final_prompt, image_bytes, mime_type, model_name or settings.DEFAULT_GEMINI_MODEL
    )


async def extract_text_ocr(*, image_bytes: bytes, mime_type: str, model_name: str | None = None) -> str:
    return await analyze_image(image_bytes=image_bytes, mime_type=mime_type, prompt=_OCR_PROMPT, model_name=model_name)


async def analyze_screenshot(
    *, image_bytes: bytes, mime_type: str, question: str | None = None, model_name: str | None = None
) -> str:
    return await analyze_image(
        image_bytes=image_bytes, mime_type=mime_type, prompt=question or _SCREENSHOT_PROMPT, model_name=model_name
    )


async def analyze_chart(
    *, image_bytes: bytes, mime_type: str, question: str | None = None, model_name: str | None = None
) -> str:
    return await analyze_image(
        image_bytes=image_bytes, mime_type=mime_type, prompt=question or _CHART_PROMPT, model_name=model_name
    )
