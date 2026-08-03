from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=300)
    body: str = Field(..., min_length=1)


class ReplyEmailRequest(BaseModel):
    body: str = Field(..., min_length=1)


class EmailMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: str
    thread_id: str | None
    from_: str | None = Field(default=None, alias="from")
    subject: str | None
    date: str | None
    snippet: str | None
    unread: bool


class SendEmailResponse(BaseModel):
    message_id: str
    thread_id: str | None
