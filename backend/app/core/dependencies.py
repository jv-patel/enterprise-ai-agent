"""
Request-scoped identity resolution.

Until the Firebase-auth phase lands, the authenticated user is resolved from
the `X-User-Id` header (the Supabase `users.id`), which the frontend already
knows after a successful login. This keeps every downstream module (agent,
notes, tasks, chat) coded against a single `get_current_user_id` dependency,
so wiring in real Firebase JWT verification later is a one-file change here
and nowhere else.
"""
from fastapi import Header

from app.core.exceptions import AuthenticationError


async def get_current_user_id(x_user_id: str = Header(..., alias="X-User-Id")) -> str:
    if not x_user_id or not x_user_id.strip():
        raise AuthenticationError("Missing X-User-Id header.")
    return x_user_id.strip()
