"""Gmail agent tools, bound to the current user via closures."""
from app.agents.tools.registry import ToolSpec
from app.services import gmail_service


def build_gmail_tools(*, user_id: str) -> list[ToolSpec]:
    async def send_email(to: str, subject: str, body: str) -> dict:
        return await gmail_service.send_email(user_id=user_id, to=to, subject=subject, body=body)

    async def read_inbox(max_results: int = 10) -> dict:
        messages = await gmail_service.read_inbox(user_id=user_id, max_results=max_results)
        return {"messages": messages}

    async def reply_email(message_id: str, body: str) -> dict:
        return await gmail_service.reply_email(user_id=user_id, message_id=message_id, body=body)

    async def delete_email(message_id: str) -> dict:
        return await gmail_service.delete_email(user_id=user_id, message_id=message_id)

    return [
        ToolSpec(
            name="send_email",
            description="Send a new email via the user's connected Gmail account.",
            parameters={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email address."},
                    "subject": {"type": "string", "description": "Email subject line."},
                    "body": {"type": "string", "description": "Plain-text email body."},
                },
                "required": ["to", "subject", "body"],
            },
            handler=send_email,
        ),
        ToolSpec(
            name="read_inbox",
            description="Read the user's most recent Gmail inbox messages (sender, subject, snippet, date).",
            parameters={
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Number of messages to fetch (1-50). Defaults to 10."}
                },
                "required": [],
            },
            handler=read_inbox,
        ),
        ToolSpec(
            name="reply_email",
            description="Reply to an existing email thread by message ID, keeping the original subject and thread.",
            parameters={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string", "description": "Gmail message ID being replied to."},
                    "body": {"type": "string", "description": "Plain-text reply body."},
                },
                "required": ["message_id", "body"],
            },
            handler=reply_email,
        ),
        ToolSpec(
            name="delete_email",
            description="Delete (move to Trash) an email by its Gmail message ID.",
            parameters={
                "type": "object",
                "properties": {"message_id": {"type": "string", "description": "Gmail message ID to delete."}},
                "required": ["message_id"],
            },
            handler=delete_email,
        ),
    ]
