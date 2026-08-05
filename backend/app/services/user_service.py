"""
User profile and settings.

Reads/updates the `users` and `user_settings` rows for the current
`X-User-Id`. Until Firebase auth lands, `bootstrap_user` is the interim way
a `users` row gets created (called once by the frontend on first visit,
before any user_id exists) — the future Firebase signup flow replaces this
function's *caller*, not the `users` table shape it writes to.
"""
import uuid
from typing import Any

from app.core.exceptions import NotFoundError
from app.database.supabase_client import get_supabase

DEFAULT_SETTINGS = {
    "theme": "system",
    "preferred_ai_model": "gemini-2.5-flash",
    "preferred_provider": "gemini",
    "voice_enabled": True,
    "notification_prefs": {},
}


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    supabase = get_supabase()
    response = supabase.table("users").select("*").eq("email", email).limit(1).execute()
    return response.data[0] if response.data else None


async def bootstrap_user(*, email: str, display_name: str | None) -> dict[str, Any]:
    """Get-or-create a users row for an email with no prior identity system.

    Interim mechanism: assigns a synthetic `firebase_uid` placeholder so the
    column stays populated/unique. When Firebase auth lands, real sign-ups
    will populate `firebase_uid` with the actual Firebase UID instead.
    """
    existing = await get_user_by_email(email)
    if existing:
        return existing

    supabase = get_supabase()
    response = (
        supabase.table("users")
        .insert(
            {
                "firebase_uid": f"local-{uuid.uuid4().hex}",
                "email": email,
                "display_name": display_name,
                "auth_provider": "password",
            }
        )
        .execute()
    )
    return response.data[0]


async def get_profile(user_id: str) -> dict[str, Any]:
    supabase = get_supabase()
    response = supabase.table("users").select("*").eq("id", user_id).limit(1).execute()
    if not response.data:
        raise NotFoundError(
            "No profile found for this user yet. Profiles are created during sign-up (Firebase auth phase)."
        )
    return response.data[0]


async def update_profile(user_id: str, *, display_name: str | None = None, photo_url: str | None = None) -> dict[str, Any]:
    await get_profile(user_id)  # 404s clearly if the user doesn't exist yet
    updates: dict[str, Any] = {}
    if display_name is not None:
        updates["display_name"] = display_name
    if photo_url is not None:
        updates["photo_url"] = photo_url

    supabase = get_supabase()
    response = supabase.table("users").update(updates).eq("id", user_id).execute()
    return response.data[0]


async def get_settings_for_user(user_id: str) -> dict[str, Any]:
    await get_profile(user_id)  # ensures the FK target exists before any get-or-create below

    supabase = get_supabase()
    response = supabase.table("user_settings").select("*").eq("user_id", user_id).limit(1).execute()
    if response.data:
        return response.data[0]

    # Get-or-create: a users row exists but settings haven't been initialized yet.
    created = supabase.table("user_settings").insert({"user_id": user_id, **DEFAULT_SETTINGS}).execute()
    return created.data[0]


async def update_settings_for_user(
    user_id: str,
    *,
    theme: str | None = None,
    preferred_ai_model: str | None = None,
    preferred_provider: str | None = None,
    voice_enabled: bool | None = None,
    notification_prefs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    await get_settings_for_user(user_id)  # ensures a row exists to update

    updates: dict[str, Any] = {}
    if theme is not None:
        updates["theme"] = theme
    if preferred_ai_model is not None:
        updates["preferred_ai_model"] = preferred_ai_model
    if preferred_provider is not None:
        updates["preferred_provider"] = preferred_provider
    if voice_enabled is not None:
        updates["voice_enabled"] = voice_enabled
    if notification_prefs is not None:
        updates["notification_prefs"] = notification_prefs

    if not updates:
        return await get_settings_for_user(user_id)

    supabase = get_supabase()
    response = supabase.table("user_settings").update(updates).eq("user_id", user_id).execute()
    return response.data[0]
