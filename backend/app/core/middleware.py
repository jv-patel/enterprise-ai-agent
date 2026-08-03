"""
Request-tracing middleware.

Attaches a unique `request_id` to every request (exposed via the
`X-Request-ID` response header and readable from `request.state.request_id`
in exception handlers), and logs method/path/status/duration for every
request — giving every error response a correlation ID that can be grepped
straight out of the logs.
"""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging_config import get_logger

logger = get_logger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "%s %s -> %s (%sms) [%s]",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response
