from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.core.exceptions import ValidationAppError
from app.schemas.vision import VisionAnalysisResponse, VisionAnalyzeRequest, VisionQuestionRequest
from app.services import file_service, storage_service, vision_service

router = APIRouter(prefix="/vision", tags=["vision"])


async def _load_image(user_id: str, file_id: str) -> tuple[bytes, str]:
    file_row = await file_service.get_uploaded_file(user_id, file_id)
    if file_row["file_type"] not in file_service.IMAGE_TYPES:
        raise ValidationAppError("This file is not an image.", error_code="not_an_image")
    content = await storage_service.download_file(file_row["storage_path"])
    mime_type = file_service.CONTENT_TYPE_MAP.get(file_row["file_type"], "application/octet-stream")
    return content, mime_type


@router.post("/analyze/{file_id}", response_model=VisionAnalysisResponse)
async def analyze_image(
    file_id: str,
    payload: VisionAnalyzeRequest = VisionAnalyzeRequest(),
    user_id: str = Depends(get_current_user_id),
) -> VisionAnalysisResponse:
    content, mime_type = await _load_image(user_id, file_id)
    result = await vision_service.analyze_image(image_bytes=content, mime_type=mime_type, prompt=payload.prompt)
    return VisionAnalysisResponse(file_id=file_id, result=result)


@router.post("/ocr/{file_id}", response_model=VisionAnalysisResponse)
async def ocr_image(file_id: str, user_id: str = Depends(get_current_user_id)) -> VisionAnalysisResponse:
    content, mime_type = await _load_image(user_id, file_id)
    result = await vision_service.extract_text_ocr(image_bytes=content, mime_type=mime_type)
    return VisionAnalysisResponse(file_id=file_id, result=result)


@router.post("/screenshot/{file_id}", response_model=VisionAnalysisResponse)
async def analyze_screenshot(
    file_id: str,
    payload: VisionQuestionRequest = VisionQuestionRequest(),
    user_id: str = Depends(get_current_user_id),
) -> VisionAnalysisResponse:
    content, mime_type = await _load_image(user_id, file_id)
    result = await vision_service.analyze_screenshot(image_bytes=content, mime_type=mime_type, question=payload.question)
    return VisionAnalysisResponse(file_id=file_id, result=result)


@router.post("/chart/{file_id}", response_model=VisionAnalysisResponse)
async def analyze_chart(
    file_id: str,
    payload: VisionQuestionRequest = VisionQuestionRequest(),
    user_id: str = Depends(get_current_user_id),
) -> VisionAnalysisResponse:
    content, mime_type = await _load_image(user_id, file_id)
    result = await vision_service.analyze_chart(image_bytes=content, mime_type=mime_type, question=payload.question)
    return VisionAnalysisResponse(file_id=file_id, result=result)
