"""
main.py — Application entry point for the AI Support Intelligence Platform.

Responsibilities:
  - FastAPI app initialization with metadata
  - CORS middleware configuration
  - Router registration under /api/v1
  - Health check endpoint
  - Startup / shutdown lifecycle hooks
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# ── 1. Config first — no dependencies ─────────────────────────────────────
from app.core.config import settings

# ── 2. Base + ALL models — populates Base.metadata before anything else ───
from app.db.base import Base            # noqa: F401  triggers model imports
from app.models.user import User        # noqa: F401  explicit safety import

# ── 3. Engine — needs Base.metadata already populated ─────────────────────
from app.db.session import engine

# ── 4. Routers — last, after models are registered ────────────────────────
from app.api.v1 import auth, tickets, users, analytics

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup & shutdown events
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up AI Support Intelligence Platform…")
    logger.info("Environment : %s", settings.ENVIRONMENT)
    logger.info("Database    : %s", str(settings.DATABASE_URL).split("@")[-1])

    if settings.ENVIRONMENT == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified (development mode).")
        logger.info("Tables registered: %s", list(Base.metadata.tables.keys()))

    yield

    logger.info("Shutting down — closing database connections…")
    await engine.dispose()
    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AI Support Intelligence Platform",
    description=(
        "A FastAPI backend providing JWT-authenticated ticket management "
        "with OpenAI-powered summarization, sentiment analysis, and "
        "priority classification."
    ),
    version="1.0.0",
    docs_url="/docs"        if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc"      if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=3600,
)


# ---------------------------------------------------------------------------
# API routers  (all versioned under /api/v1)
# ---------------------------------------------------------------------------

API_V1_PREFIX = "/api/v1"

app.include_router(auth.router,    prefix=f"{API_V1_PREFIX}/auth",    tags=["Authentication"])
app.include_router(users.router,   prefix=f"{API_V1_PREFIX}/users",   tags=["Users"])
app.include_router(tickets.router, prefix=f"{API_V1_PREFIX}/tickets", tags=["Tickets"])
app.include_router(analytics.router, prefix=f"{API_V1_PREFIX}/analytics", tags=["Analytics"])

from fastapi import Request
from fastapi.responses import PlainTextResponse
import traceback

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    return PlainTextResponse(
        content=traceback.format_exc(),
        status_code=500,
    )
# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    response_description="Service liveness and basic runtime info",
)
async def health_check() -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "version": app.version,
            "environment": settings.ENVIRONMENT,
        },
    )
