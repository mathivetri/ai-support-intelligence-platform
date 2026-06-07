"""
db/session.py — Async SQLAlchemy engine and session factory.

Provides:
  - `engine`       async engine instance (one per process)
  - `AsyncSessionLocal`  session factory used by get_db
  - `get_db`       FastAPI dependency that yields a transactional session

Usage in a route:
    from fastapi import Depends
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.db.session import get_db

    @router.get("/tickets")
    async def list_tickets(db: AsyncSession = Depends(get_db)):
        ...
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

def _build_engine() -> AsyncEngine:
    """
    Construct and return the async SQLAlchemy engine.

    create_async_engine() is called once at module import time.
    All routes share this single engine; the connection pool handles
    concurrency transparently.
    """

    # Pydantic v2 PostgresDsn must be cast to str for SQLAlchemy.
    database_url = str(settings.DATABASE_URL)

    # asyncpg does not accept the plain "postgresql://" scheme.
    # Ensure we always use "postgresql+asyncpg://".
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(
        database_url,

        # ── Connection pool ────────────────────────────────────────────
        # pool_size   — persistent connections kept alive between requests.
        # max_overflow — temporary extra connections under burst traffic.
        # pool_timeout — seconds to wait for a free connection before raising.
        # pool_recycle — recycle connections older than N seconds to avoid
        #               stale connection errors from the DB or a proxy.
        # pool_pre_ping — run a lightweight "SELECT 1" before each checkout
        #                to silently replace dead connections (important on
        #                cloud DBs that close idle connections).
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT,
        pool_recycle=1800,        # 30 minutes
        pool_pre_ping=True,

        # ── Debugging ─────────────────────────────────────────────────
        # echo=True logs every SQL statement — useful in development,
        # must be False in production to avoid credential/data leaks.
        echo=settings.is_development,
        echo_pool=False,          # set True to trace pool checkout events

        # ── Execution options ──────────────────────────────────────────
        # Recommended for asyncpg: expire_on_commit=False is set on the
        # session factory below, not the engine.
        future=True,              # SQLAlchemy 2.0 style (always True in 2.x)
    )

    logger.info(
        "Async engine created — host: %s, pool_size: %d, max_overflow: %d",
        str(settings.DATABASE_URL).split("@")[-1],  # mask credentials
        settings.DB_POOL_SIZE,
        settings.DB_MAX_OVERFLOW,
    )

    return engine


engine: AsyncEngine = _build_engine()


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,

    # Do NOT expire ORM objects after commit.
    # With async SQLAlchemy, accessing an expired attribute outside the
    # session context triggers a lazy-load which fails in async code.
    expire_on_commit=False,

    # Autoflush=True (default) flushes pending changes before every query,
    # so reads always see the latest in-transaction writes.
    autoflush=True,

    # autocommit=False (default) — every session runs inside a transaction
    # that must be explicitly committed or rolled back.
    autocommit=False,

    class_=AsyncSession,
)


# ---------------------------------------------------------------------------
# FastAPI dependency — get_db
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a transactional database session for the duration of one request.

    Lifecycle per request:
      1. A new AsyncSession is opened (checked out from the pool).
      2. The session is yielded to the route handler / service layer.
      3. On success  → session.commit() persists all changes.
      4. On any exception → session.rollback() discards all changes,
         then the exception is re-raised so FastAPI returns an error response.
      5. session.close() returns the connection to the pool in all cases.

    The try/except/finally block guarantees that the connection is always
    returned to the pool — even if the route handler raises an unhandled error.

    Inject into any route with:
        db: AsyncSession = Depends(get_db)
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as exc:
            await session.rollback()
            logger.error("Database error — transaction rolled back: %s", exc)
            raise
        except Exception as exc:
            await session.rollback()
            logger.error("Unexpected error — transaction rolled back: %s", exc)
            raise


# ---------------------------------------------------------------------------
# Optional utility — get a transactional connection (for raw SQL / migrations)
# ---------------------------------------------------------------------------

async def get_connection() -> AsyncGenerator[AsyncConnection, None]:
    """
    Yield a raw AsyncConnection for DDL statements or raw SQL that bypasses
    the ORM.  Prefer get_db for all normal CRUD operations.
    """
    async with engine.begin() as connection:
        try:
            yield connection
        except SQLAlchemyError as exc:
            logger.error("Connection-level error: %s", exc)
            raise


# ---------------------------------------------------------------------------
# Health-check helper — verify the DB is reachable
# ---------------------------------------------------------------------------

async def check_db_connection() -> dict[str, str]:
    """
    Run a lightweight query to confirm the database is reachable.
    Called by a /readiness endpoint, not the /health liveness probe.

    Returns:
        {"status": "ok", "detail": "..."}  on success
        {"status": "error", "detail": "..."} on failure  (caller should HTTP 503)
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "detail": "Database connection successful."}
    except SQLAlchemyError as exc:
        logger.error("Database health check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}