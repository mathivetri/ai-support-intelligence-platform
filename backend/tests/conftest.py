"""
conftest.py — shared pytest fixtures for the backend test suite.

Strategy:
  - A dedicated `<dbname>_test` database (never the real one).
  - Each test runs against a freshly created schema and inside a transaction
    that is rolled back at the end, so tests are isolated and order-independent.
  - get_db is overridden so the app and the test share one session.
  - The Groq AI call is mocked (autouse) so tests never hit the network.
  - The rate limiter is disabled (autouse) so auth tests don't trip 429s.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.schemas.ticket import TicketPriority, TicketSentiment


def _test_db_url() -> str:
    """Derive '<dbname>_test' from the configured DATABASE_URL."""
    url = make_url(str(settings.DATABASE_URL))
    if "+asyncpg" not in url.drivername:
        url = url.set(drivername="postgresql+asyncpg")
    url = url.set(database=f"{url.database}_test")
    return url.render_as_string(hide_password=False)


@pytest_asyncio.fixture
async def db_session():
    """Fresh schema + a rolled-back transaction per test."""
    engine = create_async_engine(_test_db_url(), poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, expire_on_commit=False)

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """httpx AsyncClient wired to the app, using the test session."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def mock_ai(monkeypatch):
    """Replace the Groq call with a deterministic stub — no network in tests."""
    from app.services import ai_service

    async def _fake_analyse(title: str, description: str):
        return ai_service.TicketAIResult(
            summary="Mocked AI summary.",
            sentiment=TicketSentiment.NEUTRAL,
            priority=TicketPriority.MEDIUM,
            raw_response="{}",
        )

    monkeypatch.setattr(ai_service, "analyse_ticket", _fake_analyse)


@pytest.fixture(autouse=True)
def disable_rate_limit():
    """Turn off slowapi so auth tests can fire many requests without 429s."""
    from app.core.limiter import limiter

    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest_asyncio.fixture
async def auth_headers(client):
    """Register a default user and return Bearer auth headers."""
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "alice",
            "email": "alice@example.com",
            "password": "Secure123",
            "confirm_password": "Secure123",
        },
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
