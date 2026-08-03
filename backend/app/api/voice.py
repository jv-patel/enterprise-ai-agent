"""
Voice API.

REST endpoints cover the request/response voice flows (upload a full audio
clip, get a full response). The `/stream` WebSocket provides real-time,
incremental speech-to-text: the Google Cloud Speech streaming client is a
synchronous, thread-blocking gRPC generator, so it's run in a background
thread and bridged to the async WebSocket loop via a thread-safe queue.
"""
import asyncio
import base64
import queue
import threading

from fastapi import APIRouter, Depends, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from google.cloud import speech

from app.agents.coordinator import run_agent
from app.config import get_settings
from app.core.dependencies import get_current_user_id
from app.core.exceptions import ValidationAppError
from app.core.logging_config import get_logger
from app.schemas.voice import SynthesizeRequest, TranscribeResponse, VoiceChatResponse
from app.services import voice_service

logger = get_logger(__name__)
router = APIRouter(prefix="/voice", tags=["voice"])

_CONTENT_TYPE_ENCODING_MAP = {
    "audio/webm": "WEBM_OPUS",
    "audio/ogg": "OGG_OPUS",
    "audio/wav": "LINEAR16",
    "audio/x-wav": "LINEAR16",
    "audio/mpeg": "MP3",
    "audio/mp3": "MP3",
}


def _infer_encoding(content_type: str | None) -> str:
    if not content_type:
        return "WEBM_OPUS"
    base_type = content_type.split(";")[0].strip().lower()
    return _CONTENT_TYPE_ENCODING_MAP.get(base_type, "WEBM_OPUS")


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(file: UploadFile = File(...), user_id: str = Depends(get_current_user_id)) -> TranscribeResponse:
    audio_bytes = await file.read()
    encoding_name = _infer_encoding(file.content_type)
    transcript = await voice_service.transcribe_audio(audio_bytes=audio_bytes, encoding_name=encoding_name)
    return TranscribeResponse(transcript=transcript)


@router.post("/synthesize")
async def synthesize(payload: SynthesizeRequest, user_id: str = Depends(get_current_user_id)) -> Response:
    audio_bytes = await voice_service.synthesize_speech(
        text=payload.text, voice_name=payload.voice_name, language_code=payload.language_code
    )
    return Response(content=audio_bytes, media_type="audio/mpeg")


@router.post("/chat", response_model=VoiceChatResponse)
async def voice_chat(
    file: UploadFile = File(...),
    chat_id: str | None = Form(default=None),
    user_id: str = Depends(get_current_user_id),
) -> VoiceChatResponse:
    audio_bytes = await file.read()
    encoding_name = _infer_encoding(file.content_type)
    transcript = await voice_service.transcribe_audio(audio_bytes=audio_bytes, encoding_name=encoding_name)

    if not transcript.strip():
        raise ValidationAppError("Could not understand the audio. Please try again.", error_code="empty_transcript")

    outcome = await run_agent(user_id=user_id, chat_id=chat_id, user_message=transcript)
    answer_audio = await voice_service.synthesize_speech(text=outcome.answer)

    return VoiceChatResponse(
        run_id=outcome.run_id,
        chat_id=outcome.chat_id,
        transcript=transcript,
        answer=outcome.answer,
        answer_audio_base64=base64.b64encode(answer_audio).decode(),
    )


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket) -> None:
    """Real-time streaming speech-to-text. Client sends raw WEBM/Opus audio
    chunks as binary WebSocket frames; server sends back JSON
    `{"transcript": str, "is_final": bool}` messages as recognition results
    arrive, and closes when the client disconnects."""
    await websocket.accept()

    settings = get_settings()
    loop = asyncio.get_event_loop()
    audio_queue: "queue.Queue[bytes | None]" = queue.Queue()
    result_queue: asyncio.Queue = asyncio.Queue()
    stop_event = threading.Event()

    def request_generator():
        streaming_config = speech.StreamingRecognitionConfig(
            config=speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code=settings.GOOGLE_STT_LANGUAGE_CODE,
                enable_automatic_punctuation=True,
            ),
            interim_results=True,
        )
        yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
        while not stop_event.is_set():
            chunk = audio_queue.get()
            if chunk is None:
                return
            yield speech.StreamingRecognizeRequest(audio_content=chunk)

    def run_streaming() -> None:
        client = speech.SpeechClient()
        try:
            responses = client.streaming_recognize(requests=request_generator())
            for response in responses:
                for result in response.results:
                    if not result.alternatives:
                        continue
                    payload = {"transcript": result.alternatives[0].transcript, "is_final": result.is_final}
                    asyncio.run_coroutine_threadsafe(result_queue.put(payload), loop)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Streaming STT session failed")
            asyncio.run_coroutine_threadsafe(result_queue.put({"error": str(exc)}), loop)
        finally:
            asyncio.run_coroutine_threadsafe(result_queue.put(None), loop)

    worker = threading.Thread(target=run_streaming, daemon=True)
    worker.start()

    async def forward_results() -> None:
        while True:
            item = await result_queue.get()
            if item is None:
                break
            await websocket.send_json(item)

    forward_task = asyncio.create_task(forward_results())

    try:
        while True:
            data = await websocket.receive_bytes()
            audio_queue.put(data)
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        audio_queue.put(None)
        await forward_task
