from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.notes import NoteCreateRequest, NoteResponse, NoteUpdateRequest
from app.services import notes_service

router = APIRouter(prefix="/notes", tags=["notes"])


@router.post("", response_model=NoteResponse, status_code=201)
async def create_note(payload: NoteCreateRequest, user_id: str = Depends(get_current_user_id)) -> NoteResponse:
    note = await notes_service.create_note(user_id=user_id, title=payload.title, content=payload.content, tags=payload.tags)
    return NoteResponse(**note)


@router.get("", response_model=list[NoteResponse])
async def list_notes(tag: str | None = None, user_id: str = Depends(get_current_user_id)) -> list[NoteResponse]:
    notes = await notes_service.list_notes(user_id, tag=tag)
    return [NoteResponse(**n) for n in notes]


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(note_id: str, user_id: str = Depends(get_current_user_id)) -> NoteResponse:
    note = await notes_service.get_note(user_id, note_id)
    return NoteResponse(**note)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(note_id: str, payload: NoteUpdateRequest, user_id: str = Depends(get_current_user_id)) -> NoteResponse:
    note = await notes_service.update_note(
        user_id=user_id, note_id=note_id, title=payload.title, content=payload.content, tags=payload.tags
    )
    return NoteResponse(**note)


@router.delete("/{note_id}", status_code=204)
async def delete_note(note_id: str, user_id: str = Depends(get_current_user_id)) -> None:
    await notes_service.delete_note(user_id, note_id)
