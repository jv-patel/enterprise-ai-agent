"""Google Calendar integration via the Calendar API."""
import asyncio
from datetime import datetime, timezone
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.exceptions import ExternalServiceError, NotFoundError
from app.core.logging_config import get_logger
from app.services import google_oauth_service

logger = get_logger(__name__)


async def _build_calendar_client(user_id: str):
    creds = await google_oauth_service.get_valid_credentials(user_id)
    return await asyncio.to_thread(build, "calendar", "v3", credentials=creds)


def _handle_http_error(exc: HttpError, context: str) -> None:
    logger.error("Calendar API error during %s: %s", context, exc)
    if exc.resp.status == 404:
        raise NotFoundError(f"Calendar event not found during {context}.") from exc
    raise ExternalServiceError(f"Calendar API error during {context}: {exc}", error_code="calendar_error") from exc


def _event_summary(event: dict) -> dict[str, Any]:
    start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
    end = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
    return {
        "event_id": event["id"],
        "summary": event.get("summary"),
        "description": event.get("description"),
        "start": start,
        "end": end,
        "location": event.get("location"),
        "attendees": [a.get("email") for a in event.get("attendees", [])],
        "html_link": event.get("htmlLink"),
    }


async def create_event(
    *,
    user_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    description: str | None = None,
    location: str | None = None,
    attendee_emails: list[str] | None = None,
) -> dict[str, Any]:
    service = await _build_calendar_client(user_id)
    body = {
        "summary": summary,
        "description": description,
        "location": location,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
        "attendees": [{"email": e} for e in attendee_emails] if attendee_emails else [],
    }

    def _insert():
        return service.events().insert(calendarId="primary", body=body).execute()

    try:
        event = await asyncio.to_thread(_insert)
    except HttpError as exc:
        _handle_http_error(exc, "create_event")

    return _event_summary(event)


async def update_event(
    *,
    user_id: str,
    event_id: str,
    summary: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    location: str | None = None,
) -> dict[str, Any]:
    service = await _build_calendar_client(user_id)

    def _get():
        return service.events().get(calendarId="primary", eventId=event_id).execute()

    try:
        event = await asyncio.to_thread(_get)
    except HttpError as exc:
        _handle_http_error(exc, "update_event")

    if summary is not None:
        event["summary"] = summary
    if description is not None:
        event["description"] = description
    if location is not None:
        event["location"] = location
    if start_time is not None:
        event["start"] = {"dateTime": start_time}
    if end_time is not None:
        event["end"] = {"dateTime": end_time}

    def _update():
        return service.events().update(calendarId="primary", eventId=event_id, body=event).execute()

    try:
        updated = await asyncio.to_thread(_update)
    except HttpError as exc:
        _handle_http_error(exc, "update_event")

    return _event_summary(updated)


async def delete_event(*, user_id: str, event_id: str) -> dict[str, Any]:
    service = await _build_calendar_client(user_id)

    def _delete():
        service.events().delete(calendarId="primary", eventId=event_id).execute()

    try:
        await asyncio.to_thread(_delete)
    except HttpError as exc:
        _handle_http_error(exc, "delete_event")

    return {"event_id": event_id, "deleted": True}


async def list_upcoming_events(*, user_id: str, max_results: int = 10) -> list[dict[str, Any]]:
    service = await _build_calendar_client(user_id)
    now = datetime.now(timezone.utc).isoformat()

    def _list():
        return (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=min(max(max_results, 1), 50),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )

    try:
        result = await asyncio.to_thread(_list)
    except HttpError as exc:
        _handle_http_error(exc, "list_upcoming_events")

    return [_event_summary(e) for e in result.get("items", [])]
