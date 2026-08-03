from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.calendar import EventCreateRequest, EventResponse, EventUpdateRequest
from app.services import calendar_service

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.post("/events", response_model=EventResponse, status_code=201)
async def create_event(payload: EventCreateRequest, user_id: str = Depends(get_current_user_id)) -> EventResponse:
    event = await calendar_service.create_event(
        user_id=user_id,
        summary=payload.summary,
        start_time=payload.start_time,
        end_time=payload.end_time,
        description=payload.description,
        location=payload.location,
        attendee_emails=payload.attendee_emails,
    )
    return EventResponse(**event)


@router.get("/events/upcoming", response_model=list[EventResponse])
async def list_upcoming(max_results: int = 10, user_id: str = Depends(get_current_user_id)) -> list[EventResponse]:
    events = await calendar_service.list_upcoming_events(user_id=user_id, max_results=max_results)
    return [EventResponse(**e) for e in events]


@router.patch("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str, payload: EventUpdateRequest, user_id: str = Depends(get_current_user_id)
) -> EventResponse:
    event = await calendar_service.update_event(
        user_id=user_id,
        event_id=event_id,
        summary=payload.summary,
        start_time=payload.start_time,
        end_time=payload.end_time,
        description=payload.description,
        location=payload.location,
    )
    return EventResponse(**event)


@router.delete("/events/{event_id}")
async def delete_event(event_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    return await calendar_service.delete_event(user_id=user_id, event_id=event_id)
