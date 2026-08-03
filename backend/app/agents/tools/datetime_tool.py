"""Current time and current date tools, timezone-aware via IANA names."""
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.agents.tools.registry import ToolSpec
from app.core.exceptions import ValidationAppError


def _resolve_timezone(timezone: str | None) -> ZoneInfo:
    tz_name = timezone or "UTC"
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError as exc:
        raise ValidationAppError(f"Unknown timezone: {tz_name}", error_code="invalid_timezone") from exc


async def _current_time(timezone: str | None = None) -> dict:
    tz = _resolve_timezone(timezone)
    now = datetime.now(tz)
    return {"timezone": str(tz), "time": now.strftime("%H:%M:%S"), "iso": now.isoformat()}


async def _current_date(timezone: str | None = None) -> dict:
    tz = _resolve_timezone(timezone)
    now = datetime.now(tz)
    return {
        "timezone": str(tz),
        "date": now.strftime("%Y-%m-%d"),
        "weekday": now.strftime("%A"),
        "iso": now.isoformat(),
    }


_TZ_PARAM = {
    "type": "object",
    "properties": {
        "timezone": {
            "type": "string",
            "description": "IANA timezone name, e.g. 'America/New_York'. Defaults to UTC if omitted.",
        }
    },
    "required": [],
}


def build_current_time_tool() -> ToolSpec:
    return ToolSpec(
        name="current_time",
        description="Get the current time, optionally in a specific IANA timezone.",
        parameters=_TZ_PARAM,
        handler=_current_time,
    )


def build_current_date_tool() -> ToolSpec:
    return ToolSpec(
        name="current_date",
        description="Get the current date and weekday, optionally in a specific IANA timezone.",
        parameters=_TZ_PARAM,
        handler=_current_date,
    )
