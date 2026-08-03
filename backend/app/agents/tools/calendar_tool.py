"""Google Calendar agent tools, bound to the current user via closures."""
from app.agents.tools.registry import ToolSpec
from app.services import calendar_service


def build_calendar_tools(*, user_id: str) -> list[ToolSpec]:
    async def create_event(
        summary: str,
        start_time: str,
        end_time: str,
        description: str | None = None,
        location: str | None = None,
        attendee_emails: list[str] | None = None,
    ) -> dict:
        return await calendar_service.create_event(
            user_id=user_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            attendee_emails=attendee_emails,
        )

    async def update_event(
        event_id: str,
        summary: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        description: str | None = None,
        location: str | None = None,
    ) -> dict:
        return await calendar_service.update_event(
            user_id=user_id,
            event_id=event_id,
            summary=summary,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
        )

    async def delete_event(event_id: str) -> dict:
        return await calendar_service.delete_event(user_id=user_id, event_id=event_id)

    async def list_upcoming_meetings(max_results: int = 10) -> dict:
        events = await calendar_service.list_upcoming_events(user_id=user_id, max_results=max_results)
        return {"events": events}

    iso_time_desc = "ISO 8601 date-time, e.g. '2026-08-05T14:00:00-04:00'."

    return [
        ToolSpec(
            name="create_calendar_event",
            description="Create a new event on the user's primary Google Calendar.",
            parameters={
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Event title."},
                    "start_time": {"type": "string", "description": iso_time_desc},
                    "end_time": {"type": "string", "description": iso_time_desc},
                    "description": {"type": "string", "description": "Optional event description."},
                    "location": {"type": "string", "description": "Optional event location."},
                    "attendee_emails": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of attendee email addresses to invite.",
                    },
                },
                "required": ["summary", "start_time", "end_time"],
            },
            handler=create_event,
        ),
        ToolSpec(
            name="update_calendar_event",
            description="Update fields of an existing calendar event by event ID.",
            parameters={
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "ID of the event to update."},
                    "summary": {"type": "string"},
                    "start_time": {"type": "string", "description": iso_time_desc},
                    "end_time": {"type": "string", "description": iso_time_desc},
                    "description": {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["event_id"],
            },
            handler=update_event,
        ),
        ToolSpec(
            name="delete_calendar_event",
            description="Delete an event from the user's primary Google Calendar by event ID.",
            parameters={
                "type": "object",
                "properties": {"event_id": {"type": "string", "description": "ID of the event to delete."}},
                "required": ["event_id"],
            },
            handler=delete_event,
        ),
        ToolSpec(
            name="list_upcoming_meetings",
            description="List the user's upcoming Google Calendar events, soonest first.",
            parameters={
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Number of events to fetch (1-50). Defaults to 10."}
                },
                "required": [],
            },
            handler=list_upcoming_meetings,
        ),
    ]
