"""
Voice AI: Google Cloud Speech-to-Text (batch) and Text-to-Speech.

Real-time streaming STT lives in `app/api/voice.py` (WebSocket endpoint),
since it needs to bridge the synchronous streaming gRPC client to FastAPI's
async request loop — that bridging logic is request-lifecycle-specific and
doesn't belong in this stateless service module.
"""
import asyncio

from google.cloud import speech, texttospeech

from app.config import get_settings
from app.core.exceptions import ExternalServiceError, ValidationAppError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_MAX_TTS_CHUNK_CHARS = 4500  # Google TTS enforces a ~5000 byte input limit per request


def resolve_encoding(name: str) -> "speech.RecognitionConfig.AudioEncoding":
    return getattr(speech.RecognitionConfig.AudioEncoding, name, speech.RecognitionConfig.AudioEncoding.WEBM_OPUS)


def _sync_transcribe(audio_bytes: bytes, sample_rate_hertz: int, encoding, language_code: str) -> str:
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=encoding,
        sample_rate_hertz=sample_rate_hertz,
        language_code=language_code,
        enable_automatic_punctuation=True,
    )
    try:
        response = client.recognize(config=config, audio=audio)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Speech-to-text request failed")
        raise ExternalServiceError(f"Speech-to-text failed: {exc}", error_code="stt_error") from exc

    return " ".join(result.alternatives[0].transcript for result in response.results if result.alternatives)


async def transcribe_audio(
    *, audio_bytes: bytes, sample_rate_hertz: int = 48000, encoding_name: str = "WEBM_OPUS"
) -> str:
    settings = get_settings()
    encoding = resolve_encoding(encoding_name)
    return await asyncio.to_thread(
        _sync_transcribe, audio_bytes, sample_rate_hertz, encoding, settings.GOOGLE_STT_LANGUAGE_CODE
    )


def _chunk_text(text: str, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for sentence in text.replace("\n", " ").split(". "):
        piece = sentence if sentence.endswith(".") else sentence + "."
        if current_len + len(piece) > max_chars and current:
            chunks.append(" ".join(current))
            current, current_len = [], 0
        current.append(piece)
        current_len += len(piece)
    if current:
        chunks.append(" ".join(current))
    return chunks


def _sync_synthesize(text: str, voice_name: str, language_code: str) -> bytes:
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(language_code=language_code, name=voice_name)
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    try:
        response = client.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Text-to-speech request failed")
        raise ExternalServiceError(f"Text-to-speech failed: {exc}", error_code="tts_error") from exc
    return response.audio_content


async def synthesize_speech(*, text: str, voice_name: str | None = None, language_code: str | None = None) -> bytes:
    if not text.strip():
        raise ValidationAppError("Cannot synthesize empty text.", error_code="tts_empty_text")

    settings = get_settings()
    resolved_voice = voice_name or settings.GOOGLE_TTS_VOICE_NAME
    resolved_language = language_code or settings.GOOGLE_TTS_LANGUAGE_CODE

    chunks = _chunk_text(text, _MAX_TTS_CHUNK_CHARS)
    audio_parts = await asyncio.gather(
        *[asyncio.to_thread(_sync_synthesize, chunk, resolved_voice, resolved_language) for chunk in chunks]
    )
    return b"".join(audio_parts)
