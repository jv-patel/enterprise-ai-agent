from pydantic import BaseModel, Field


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice_name: str | None = None
    language_code: str | None = None


class TranscribeResponse(BaseModel):
    transcript: str


class VoiceChatResponse(BaseModel):
    run_id: str
    chat_id: str
    transcript: str
    answer: str
    answer_audio_base64: str
