from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.gmail import EmailMessage, ReplyEmailRequest, SendEmailRequest, SendEmailResponse
from app.services import gmail_service

router = APIRouter(prefix="/gmail", tags=["gmail"])


@router.post("/send", response_model=SendEmailResponse)
async def send_email(payload: SendEmailRequest, user_id: str = Depends(get_current_user_id)) -> SendEmailResponse:
    result = await gmail_service.send_email(user_id=user_id, to=payload.to, subject=payload.subject, body=payload.body)
    return SendEmailResponse(**result)


@router.get("/inbox", response_model=list[EmailMessage])
async def read_inbox(max_results: int = 10, user_id: str = Depends(get_current_user_id)) -> list[EmailMessage]:
    messages = await gmail_service.read_inbox(user_id=user_id, max_results=max_results)
    return [EmailMessage(**m) for m in messages]


@router.post("/{message_id}/reply", response_model=SendEmailResponse)
async def reply_email(
    message_id: str, payload: ReplyEmailRequest, user_id: str = Depends(get_current_user_id)
) -> SendEmailResponse:
    result = await gmail_service.reply_email(user_id=user_id, message_id=message_id, body=payload.body)
    return SendEmailResponse(**result)


@router.delete("/{message_id}")
async def delete_email(message_id: str, user_id: str = Depends(get_current_user_id)) -> dict:
    return await gmail_service.delete_email(user_id=user_id, message_id=message_id)
