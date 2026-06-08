"""
services/analytics_service.py — Aggregate analytics over the Ticket entity.

Computes dashboard-style metrics for a single user's tickets:
  - Total tickets
  - Open tickets
  - Resolved tickets
  - Tickets grouped by priority
  - Tickets grouped by sentiment

Design principles:
  - All counts are computed in PostgreSQL via COUNT + GROUP BY — rows are
    never loaded into Python, so the cost is O(result groups), not O(tickets).
  - Owner-scoped: every query filters on owner_id, matching the IDOR-safe
    pattern used throughout ticket_service.py. A user only ever sees their
    own analytics.
  - Async throughout — never blocks the event loop.

Public API:
  get_ticket_analytics(db, owner_id) -> TicketAnalytics
"""

from __future__ import annotations

import logging
import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import (
    Ticket,
    TicketPriority,
    TicketSentiment,
    TicketStatus,
)

logger = logging.getLogger(__name__)

# Bucket key used for tickets whose priority/sentiment has not yet been
# set by the AI service (NULL in the database) or holds an unknown value.
_UNCLASSIFIED = "unclassified"


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------
# Defined here to keep the analytics feature self-contained. If the project
# grows, move this to schemas/analytics.py to mirror schemas/ticket.py.

class TicketAnalytics(BaseModel):
    """Aggregate ticket metrics for a single user."""

    total_tickets: int = Field(description="Total number of tickets owned by the user.")
    open_tickets: int = Field(description="Tickets currently in the 'open' state.")
    resolved_tickets: int = Field(description="Tickets currently in the 'resolved' state.")

    tickets_by_priority: dict[str, int] = Field(
        description=(
            "Ticket count per priority (low/medium/high/critical), plus "
            "'unclassified' for tickets the AI has not yet prioritised. "
            "Every key is always present, defaulting to 0."
        ),
    )
    tickets_by_sentiment: dict[str, int] = Field(
        description=(
            "Ticket count per sentiment (positive/neutral/negative), plus "
            "'unclassified' for tickets the AI has not yet analysed. "
            "Every key is always present, defaulting to 0."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_tickets": 42,
                "open_tickets": 17,
                "resolved_tickets": 20,
                "tickets_by_priority": {
                    "low": 8,
                    "medium": 15,
                    "high": 12,
                    "critical": 5,
                    "unclassified": 2,
                },
                "tickets_by_sentiment": {
                    "positive": 6,
                    "neutral": 14,
                    "negative": 20,
                    "unclassified": 2,
                },
            }
        }
    )


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _count_total(db: AsyncSession, owner_id: uuid.UUID) -> int:
    """Return the total number of tickets owned by owner_id."""
    result = await db.execute(
        select(func.count()).where(Ticket.owner_id == owner_id)
    )
    return result.scalar_one()


async def _count_by_column(
    db: AsyncSession,
    owner_id: uuid.UUID,
    column,
) -> dict[str | None, int]:
    """
    Return a {column_value: count} map for the given column, scoped to owner_id.

    A single `SELECT column, COUNT(*) ... GROUP BY column` query. The map may
    contain a None key for rows where the column is NULL (e.g. AI fields not
    yet populated).
    """
    result = await db.execute(
        select(column, func.count())
        .where(Ticket.owner_id == owner_id)
        .group_by(column)
    )
    return {value: count for value, count in result.all()}


def _bucket(raw: dict[str | None, int], enum_cls) -> dict[str, int]:
    """
    Normalise a raw {db_value: count} map into a stable, 0-filled bucket dict.

    Every member of `enum_cls` is present as a key (defaulting to 0), plus an
    'unclassified' bucket that absorbs NULLs and any value not in the enum.
    """
    buckets: dict[str, int] = {member.value: 0 for member in enum_cls}
    buckets[_UNCLASSIFIED] = 0

    for value, count in raw.items():
        if value in buckets and value != _UNCLASSIFIED:
            buckets[value] = count
        else:
            buckets[_UNCLASSIFIED] += count

    return buckets


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_ticket_analytics(
    db: AsyncSession,
    owner_id: uuid.UUID,
) -> TicketAnalytics:
    """
    Compute aggregate ticket analytics for a single user.

    Runs four aggregate queries (total, by-status, by-priority, by-sentiment),
    all scoped to owner_id. Open and resolved counts are derived from the
    status breakdown so the lifecycle is only scanned once.

    Args:
        db:       Async SQLAlchemy session.
        owner_id: UUID of the user whose tickets are being analysed.

    Returns:
        TicketAnalytics with totals and priority/sentiment breakdowns.
    """
    total = await _count_total(db, owner_id)

    by_status = await _count_by_column(db, owner_id, Ticket.status)
    by_priority = await _count_by_column(db, owner_id, Ticket.priority)
    by_sentiment = await _count_by_column(db, owner_id, Ticket.sentiment)

    analytics = TicketAnalytics(
        total_tickets=total,
        open_tickets=by_status.get(TicketStatus.OPEN.value, 0),
        resolved_tickets=by_status.get(TicketStatus.RESOLVED.value, 0),
        tickets_by_priority=_bucket(by_priority, TicketPriority),
        tickets_by_sentiment=_bucket(by_sentiment, TicketSentiment),
    )

    logger.info(
        "Computed analytics for owner_id=%s: total=%d open=%d resolved=%d",
        owner_id, total, analytics.open_tickets, analytics.resolved_tickets,
    )

    return analytics
