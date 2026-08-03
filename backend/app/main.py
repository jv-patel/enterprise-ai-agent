"""
Enterprise AI Personal Agent — FastAPI application entrypoint.

New feature routers are registered here as each phase lands. Phase 1 wires
up the app skeleton: settings, structured logging, CORS, global error
handling, and a health check endpoint.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.agent import router as agent_router
from app.api.calendar import router as calendar_router
from app.api.dashboard import router as dashboard_router
from app.api.drive import router as drive_router
from app.api.files import router as files_router
from app.api.gmail import router as gmail_router
from app.api.google import router as google_router
from app.api.health import router as health_router
from app.api.notes import router as notes_router
from app.api.notifications import router as notifications_router
from app.api.tasks import router as tasks_router
from app.api.users import router as users_router
from app.api.vision import router as vision_router
from app.api.voice import router as voice_router
from app.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware

configure_logging()
logger = get_logger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

register_exception_handlers(app)

app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(agent_router, prefix=settings.API_V1_PREFIX)
app.include_router(notes_router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks_router, prefix=settings.API_V1_PREFIX)
app.include_router(google_router, prefix=settings.API_V1_PREFIX)
app.include_router(gmail_router, prefix=settings.API_V1_PREFIX)
app.include_router(calendar_router, prefix=settings.API_V1_PREFIX)
app.include_router(drive_router, prefix=settings.API_V1_PREFIX)
app.include_router(files_router, prefix=settings.API_V1_PREFIX)
app.include_router(vision_router, prefix=settings.API_V1_PREFIX)
app.include_router(voice_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(notifications_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("%s starting up in '%s' environment", settings.APP_NAME, settings.ENVIRONMENT)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("%s shutting down", settings.APP_NAME)
