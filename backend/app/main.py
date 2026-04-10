"""
FastAPI application entry point.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.config import get_settings

settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)
logging.basicConfig(level=settings.log_level)


# ── LangSmith optional setup ──────────────────────────────────────────────────

if settings.langsmith_enabled:
    import os
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.langsmith_api_key
    os.environ["LANGCHAIN_PROJECT"] = settings.langsmith_project


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    import asyncio
    from app.db.client import get_db_pool, close_db_pool

    logger.info("startup", env=settings.app_env)

    # Start embedded worker when EMBEDDED_WORKER=true (default on Render free tier
    # where a separate background worker service is not available).
    await get_db_pool()

    worker_task = None
    if settings.embedded_worker:
        from worker.main import run_worker
        worker_task = asyncio.create_task(run_worker())
        logger.info("embedded_worker_started")

    yield

    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
        logger.info("embedded_worker_stopped")
    await close_db_pool()

    logger.info("shutdown")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PM Sidekick API",
    version="0.1.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
    lifespan=lifespan,
)

_cors_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
_allow_all_origins = "*" in _cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all_origins else _cors_origins,
    # allow_credentials must be False when allow_origins=["*"] (browser spec)
    # Auth is Bearer token in Authorization header — cookies are not used.
    allow_credentials=not _allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request logging middleware ────────────────────────────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next: object) -> Response:
    start = time.perf_counter()
    response: Response = await call_next(request)  # type: ignore[operator]
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 2),
    )
    return response


# ── Error handlers ────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception", path=request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "code": "INTERNAL_ERROR"},
    )


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(api_router, prefix="/api/v1")


@app.get("/healthz", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readiness() -> dict:
    # Could add DB connectivity check here
    return {"status": "ready"}


@app.get("/version", include_in_schema=False)
async def version() -> dict:
    import os
    return {
        "commit": os.environ.get("RENDER_GIT_COMMIT", "unknown"),
        "embedded_worker": settings.embedded_worker,
        "app_env": settings.app_env,
    }
