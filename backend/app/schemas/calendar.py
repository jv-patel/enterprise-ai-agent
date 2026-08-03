from pydantic import BaseModel, Field


class EventCreateRequest(BaseModel):
    summary: str = Field(..., min_length=1, max_length=300)
    start_time: str = Field(..., description="ISO 8601 date-time")
    end_time: str = Field(..., description="ISO 8601 date-time")
    description: str | None = None
    location: str | None = None
    attendee_emails: list[str] = Field(default_factory=list)


class EventUpdateRequest(BaseModel):
    summary: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    description: str | None = None
    location: str | None = None


class EventResponse(BaseModel):
    event_id: str
    summary: str | None
    description: str | None
    start: str | None
    end: str | None
    location: str | None
    attendees: list[str | None]
    html_link: str | None
