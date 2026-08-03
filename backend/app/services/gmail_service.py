"""
Gmail integration via the Gmail API (googleapiclient), authenticated per-user
through `google_oauth_service.get_valid_credentials`.

`delete_email` moves messages to Trash (`messages.trash`) rather than
permanent deletion, which requires the much broader `https://mail.google.com/`
scope. Trashed messages are recoverable for 30 days, matching Gmail's normal
UI behavior and keeping the granted scope minimal.
"""
import asyncio
import base64
from email.mime.text import MIMEText
from typing import Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.exceptions import ExternalServiceError, NotFoundError
from app.core.logging_config import get_logger
from app.services import google_oauth_service

logger = get_logger(__name__)


async def _build_gmail_client(user_id: str):
    creds = await google_oauth_service.get_valid_credentials(user_id)
    return await asyncio.to_thread(build, "gmail", "v1", credentials=creds)


def _handle_http_error(exc: HttpError, context: str) -> None:
    logger.error("Gmail API error during %s: %s", context, exc)
    if exc.resp.status == 404:
        raise NotFoundError(f"Gmail resource not found during {context}.") from exc
    raise ExternalServiceError(f"Gmail API error during {context}: {exc}", error_code="gmail_error") from exc


def _encode_message(mime_message: MIMEText) -> dict:
    raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode()
    return {"raw": raw}


async def send_email(*, user_id: str, to: str, subject: str, body: str) -> dict[str, Any]:
    service = await _build_gmail_client(user_id)
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject

    def _send():
        return service.users().messages().send(userId="me", body=_encode_message(message)).execute()

    try:
        result = await asyncio.to_thread(_send)
    except HttpError as exc:
        _handle_http_error(exc, "send_email")
    return {"message_id": result["id"], "thread_id": result.get("threadId")}


async def read_inbox(*, user_id: str, max_results: int = 10) -> list[dict[str, Any]]:
    service = await _build_gmail_client(user_id)

    def _list():
        return (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=min(max(max_results, 1), 50))
            .execute()
        )

    try:
        listing = await asyncio.to_thread(_list)
    except HttpError as exc:
        _handle_http_error(exc, "read_inbox")

    message_ids = [m["id"] for m in listing.get("messages", [])]

    def _get_one(message_id: str) -> dict[str, Any]:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        return {
            "message_id": msg["id"],
            "thread_id": msg.get("threadId"),
            "from": headers.get("From"),
            "subject": headers.get("Subject"),
            "date": headers.get("Date"),
            "snippet": msg.get("snippet"),
            "unread": "UNREAD" in msg.get("labelIds", []),
        }

    try:
        messages = await asyncio.gather(*[asyncio.to_thread(_get_one, mid) for mid in message_ids])
    except HttpError as exc:
        _handle_http_error(exc, "read_inbox")

    return list(messages)


async def reply_email(*, user_id: str, message_id: str, body: str) -> dict[str, Any]:
    service = await _build_gmail_client(user_id)

    def _get_original():
        return (
            service.users()
            .messages()
            .get(userId="me", id=message_id, format="metadata", metadataHeaders=["From", "Subject", "Message-ID", "References"])
            .execute()
        )

    try:
        original = await asyncio.to_thread(_get_original)
    except HttpError as exc:
        _handle_http_error(exc, "reply_email")

    headers = {h["name"]: h["value"] for h in original.get("payload", {}).get("headers", [])}
    subject = headers.get("Subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    reply = MIMEText(body)
    reply["to"] = headers.get("From", "")
    reply["subject"] = subject
    if headers.get("Message-ID"):
        reply["In-Reply-To"] = headers["Message-ID"]
        reply["References"] = f"{headers.get('References', '')} {headers['Message-ID']}".strip()

    payload = _encode_message(reply)
    payload["threadId"] = original.get("threadId")

    def _send():
        return service.users().messages().send(userId="me", body=payload).execute()

    try:
        result = await asyncio.to_thread(_send)
    except HttpError as exc:
        _handle_http_error(exc, "reply_email")

    return {"message_id": result["id"], "thread_id": result.get("threadId")}


async def delete_email(*, user_id: str, message_id: str) -> dict[str, Any]:
    service = await _build_gmail_client(user_id)

    def _trash():
        return service.users().messages().trash(userId="me", id=message_id).execute()

    try:
        await asyncio.to_thread(_trash)
    except HttpError as exc:
        _handle_http_error(exc, "delete_email")

    return {"message_id": message_id, "trashed": True}
