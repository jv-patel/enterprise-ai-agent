from datetime import datetime

from pydantic import BaseModel, Field


class UploadedFileResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    created_at: datetime
    summary: str | None = None


class FileContentResponse(BaseModel):
    file_id: str
    file_name: str
    content: str
    truncated: bool


class FileSummaryResponse(BaseModel):
    file_id: str
    summary: str


class FileQuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


class FileAnswerResponse(BaseModel):
    file_id: str
    question: str
    answer: str
