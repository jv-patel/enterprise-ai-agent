from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.config import get_settings
from app.core.dependencies import get_current_user_id
from app.core.exceptions import ValidationAppError
from app.schemas.files import (
    FileAnswerResponse,
    FileContentResponse,
    FileQuestionRequest,
    FileSummaryResponse,
    UploadedFileResponse,
)
from app.services import file_service

router = APIRouter(prefix="/files", tags=["files"])


@router.post("/upload", response_model=UploadedFileResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    chat_id: str | None = Form(default=None),
    user_id: str = Depends(get_current_user_id),
) -> UploadedFileResponse:
    settings = get_settings()
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_BYTES:
        raise ValidationAppError(
            f"File exceeds the {settings.MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.",
            error_code="file_too_large",
        )

    file_type = file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else ""
    record = await file_service.upload_and_process_file(
        user_id=user_id,
        chat_id=chat_id,
        file_name=file.filename or "upload",
        content=content,
        file_type=file_type,
    )
    return UploadedFileResponse(**record)


@router.get("", response_model=list[UploadedFileResponse])
async def list_files(chat_id: str | None = None, user_id: str = Depends(get_current_user_id)) -> list[UploadedFileResponse]:
    files = await file_service.list_uploaded_files(user_id, chat_id=chat_id)
    return [UploadedFileResponse(**f) for f in files]


@router.get("/{file_id}", response_model=FileContentResponse)
async def get_file_content(file_id: str, user_id: str = Depends(get_current_user_id)) -> FileContentResponse:
    result = await file_service.read_file_content(user_id, file_id)
    return FileContentResponse(**result)


@router.post("/{file_id}/summarize", response_model=FileSummaryResponse)
async def summarize_file(file_id: str, user_id: str = Depends(get_current_user_id)) -> FileSummaryResponse:
    result = await file_service.summarize_file(user_id, file_id)
    return FileSummaryResponse(**result)


@router.post("/{file_id}/ask", response_model=FileAnswerResponse)
async def ask_file_question(
    file_id: str, payload: FileQuestionRequest, user_id: str = Depends(get_current_user_id)
) -> FileAnswerResponse:
    result = await file_service.ask_question_about_file(user_id, file_id, payload.question)
    return FileAnswerResponse(**result)
