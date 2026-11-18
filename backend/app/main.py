import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import alerts, auth, dashboard, logs, metrics, servers, settings as settings_router, ws
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.database.init_db import create_tables_and_seed
from app.database.session import SessionLocal, engine
from app.services.background_tasks import background_monitor_loop
from app.websocket.manager import ws_manager

settings = get_settings()
configure_logging(settings.LOG_LEVEL)
logger = logging.getLogger(__name__)
APP_START_TIME = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting %s v%s (%s)", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)
    create_tables_and_seed(engine, SessionLocal)

    stop_event = asyncio.Event()
    bg_task = None
    if not settings.DISABLE_BACKGROUND_TASKS:
        bg_task = asyncio.create_task(background_monitor_loop(stop_event))

    yield

    if bg_task:
        stop_event.set()
        bg_task.cancel()
        try:
            await bg_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title="SentinelOps API",
    description="Centralized Linux Server Monitoring, Alerting & Log Observability Platform",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Agent-Token"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict):
        body = exc.detail
    else:
        body = {"error": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Request validation failed.",
            "details": exc.errors(),
        },
    )


@app.get("/health", tags=["Health"])
def health_check():
    db_status = "connected"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        logger.error("Health check DB failure: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "database": "disconnected",
                "version": settings.APP_VERSION,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    uptime = int((datetime.now(timezone.utc) - APP_START_TIME).total_seconds())
    return {
        "status": "healthy",
        "database": db_status,
        "version": settings.APP_VERSION,
        "uptime_seconds": uptime,
        "websocket_clients": ws_manager.active_count,
        "demo_mode": settings.DEMO_MODE,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


app.include_router(auth.router)
app.include_router(servers.router)
app.include_router(metrics.router)
app.include_router(alerts.router)
app.include_router(logs.router)
app.include_router(settings_router.router)
app.include_router(dashboard.router)
app.include_router(ws.router)

# Optional single-port local mode: serve built React SPA when SERVE_STATIC_FRONTEND=true
import os as _os
from pathlib import Path as _Path
from fastapi.responses import FileResponse as _FileResponse
from fastapi.staticfiles import StaticFiles as _StaticFiles

if _os.getenv("SERVE_STATIC_FRONTEND", "false").lower() in ("1", "true", "yes"):
    _dist_dir = _Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if _dist_dir.exists():
        _assets_dir = _dist_dir / "assets"
        if _assets_dir.exists():
            app.mount("/assets", _StaticFiles(directory=str(_assets_dir)), name="frontend-assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            candidate = _dist_dir / full_path
            if full_path and candidate.is_file():
                return _FileResponse(str(candidate))
            return _FileResponse(str(_dist_dir / "index.html"))


