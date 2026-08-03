from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.notifications import MarkAllReadResponse, NotificationResponse
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False, limit: int = 50, user_id: str = Depends(get_current_user_id)
) -> list[NotificationResponse]:
    notifications = await notification_service.list_notifications(user_id, unread_only=unread_only, limit=limit)
    return [NotificationResponse(**n) for n in notifications]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(notification_id: str, user_id: str = Depends(get_current_user_id)) -> NotificationResponse:
    notification = await notification_service.mark_notification_read(user_id, notification_id)
    return NotificationResponse(**notification)


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_read(user_id: str = Depends(get_current_user_id)) -> MarkAllReadResponse:
    count = await notification_service.mark_all_read(user_id)
    return MarkAllReadResponse(marked_read=count)


@router.post("/check-reminders", response_model=list[NotificationResponse])
async def check_reminders(user_id: str = Depends(get_current_user_id)) -> list[NotificationResponse]:
    """Scans the user's due task reminders and creates notifications for them.

    Intended to be called periodically by a scheduler (see docs/DEPLOYMENT.md
    for a Render Cron Job example) since this backend has no built-in
    background scheduler.
    """
    created = await notification_service.check_due_reminders(user_id)
    return [NotificationResponse(**n) for n in created]
