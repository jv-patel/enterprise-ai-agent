from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.drive import DriveFile, DriveFileContent
from app.services import drive_service

router = APIRouter(prefix="/drive", tags=["drive"])


@router.get("/search", response_model=list[DriveFile])
async def search_files(query: str, max_results: int = 10, user_id: str = Depends(get_current_user_id)) -> list[DriveFile]:
    files = await drive_service.search_files(user_id=user_id, query=query, max_results=max_results)
    return [DriveFile(**f) for f in files]


@router.get("/files/{file_id}", response_model=DriveFileContent)
async def read_file(file_id: str, user_id: str = Depends(get_current_user_id)) -> DriveFileContent:
    result = await drive_service.read_file(user_id=user_id, file_id=file_id)
    return DriveFileContent(**result)
