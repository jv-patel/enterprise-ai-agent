from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_id
from app.schemas.users import (
    UserBootstrapRequest,
    UserProfileResponse,
    UserProfileUpdateRequest,
    UserSettingsResponse,
    UserSettingsUpdateRequest,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/bootstrap", response_model=UserProfileResponse)
async def bootstrap_user(payload: UserBootstrapRequest) -> UserProfileResponse:
    """Interim, no-auth identity creation: get-or-create a users row by
    email. Used by the frontend on first visit until Firebase auth lands."""
    user = await user_service.bootstrap_user(email=payload.email, display_name=payload.display_name)
    return UserProfileResponse(**user)


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(user_id: str = Depends(get_current_user_id)) -> UserProfileResponse:
    profile = await user_service.get_profile(user_id)
    return UserProfileResponse(**profile)


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    payload: UserProfileUpdateRequest, user_id: str = Depends(get_current_user_id)
) -> UserProfileResponse:
    profile = await user_service.update_profile(user_id, display_name=payload.display_name, photo_url=payload.photo_url)
    return UserProfileResponse(**profile)


@router.get("/me/settings", response_model=UserSettingsResponse)
async def get_my_settings(user_id: str = Depends(get_current_user_id)) -> UserSettingsResponse:
    settings = await user_service.get_settings_for_user(user_id)
    return UserSettingsResponse(**settings)


@router.patch("/me/settings", response_model=UserSettingsResponse)
async def update_my_settings(
    payload: UserSettingsUpdateRequest, user_id: str = Depends(get_current_user_id)
) -> UserSettingsResponse:
    settings = await user_service.update_settings_for_user(
        user_id,
        theme=payload.theme,
        preferred_ai_model=payload.preferred_ai_model,
        preferred_provider=payload.preferred_provider,
        voice_enabled=payload.voice_enabled,
        notification_prefs=payload.notification_prefs,
    )
    return UserSettingsResponse(**settings)
