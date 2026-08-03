from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.dashboard import ActivityLogEntry, AiStatistics, UsageAnalytics
from app.services import activity_service, analytics_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/analytics", response_model=UsageAnalytics)
async def get_usage_analytics(user_id: str = Depends(get_current_user_id)) -> UsageAnalytics:
    data = await analytics_service.get_usage_analytics(user_id)
    return UsageAnalytics(**data)


@router.get("/ai-statistics", response_model=AiStatistics)
async def get_ai_statistics(user_id: str = Depends(get_current_user_id)) -> AiStatistics:
    data = await analytics_service.get_ai_statistics(user_id)
    return AiStatistics(**data)


@router.get("/activity", response_model=list[ActivityLogEntry])
async def get_activity_feed(limit: int = 30, user_id: str = Depends(get_current_user_id)) -> list[ActivityLogEntry]:
    activity = await activity_service.list_activity_feed(user_id, limit=limit)
    return [ActivityLogEntry(**a) for a in activity]
