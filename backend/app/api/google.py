from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse

from app.config import get_settings
from app.core.dependencies import get_current_user_id
from app.core.exceptions import AppError
from app.core.logging_config import get_logger
from app.schemas.google import GoogleAuthUrlResponse, GoogleConnectionStatus
from app.services import google_oauth_service

logger = get_logger(__name__)
router = APIRouter(prefix="/google", tags=["google"])


@router.get("/oauth/authorize", response_model=GoogleAuthUrlResponse)
async def authorize_google(user_id: str = Depends(get_current_user_id)) -> GoogleAuthUrlResponse:
    url = google_oauth_service.build_authorization_url(user_id)
    return GoogleAuthUrlResponse(authorization_url=url)


@router.get("/oauth/callback")
async def google_oauth_callback(code: str = Query(...), state: str = Query(...)) -> RedirectResponse:
    settings = get_settings()
    try:
        await google_oauth_service.handle_oauth_callback(code=code, state=state)
    except AppError:
        logger.exception("Google OAuth callback failed")
        return RedirectResponse(url=settings.GOOGLE_POST_AUTH_ERROR_REDIRECT_URL)
    return RedirectResponse(url=settings.GOOGLE_POST_AUTH_REDIRECT_URL)


@router.get("/status", response_model=GoogleConnectionStatus)
async def google_connection_status(user_id: str = Depends(get_current_user_id)) -> GoogleConnectionStatus:
    status = await google_oauth_service.get_connection_status(user_id)
    return GoogleConnectionStatus(**status)


@router.delete("/disconnect", status_code=204)
async def disconnect_google(user_id: str = Depends(get_current_user_id)) -> None:
    await google_oauth_service.disconnect(user_id)
