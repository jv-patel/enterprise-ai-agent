"""
Application-wide exception types and their FastAPI exception handlers.

Every domain module (auth, chat, agents, google integrations, files, ...)
raises one of these instead of a bare HTTPException, so error shape stays
consistent across the entire API surface.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging_config import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for all handled application errors."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"

    def __init__(self, message: str, *, error_code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code
        if status_code:
            self.status_code = status_code


class AuthenticationError(AppError):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "authentication_error"


class AuthorizationError(AppError):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "authorization_error"


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "not_found"


class ValidationAppError(AppError):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "validation_error"


class RateLimitError(AppError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "rate_limited"


class ExternalServiceError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    error_code = "external_service_error"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.warning("AppError on %s %s [%s]: %s", request.method, request.url.path, request_id, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.error_code, "message": exc.message, "request_id": request_id}},
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Unhandled error on %s %s [%s]", request.method, request.url.path, request_id)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "request_id": request_id,
                }
            },
        )
