"""
api/v1/analytics.py — Analytics route handlers.

Endpoints:
  GET /api/v1/analytics/overview      Full ticket metrics (totals + breakdowns)
  GET /api/v1/analytics/sentiment     Ticket counts grouped by sentiment
  GET /api/v1/analytics/priorities    Ticket counts grouped by priority

All endpoints require a valid JWT access token.
All metrics are scoped to the authenticated user's own tickets only.

This module is intentionally thin:
  - Declares the HTTP contract (method, path, status code, response schema)
  - Resolves the authenticated user
  - Delegates all aggregation to analytics_service
  - Returns the service result directly
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.user import UserResponse
from app.services import analytics_service
from app.services.analytics_service import TicketAnalytics

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /analytics/overview — full metrics
# ---------------------------------------------------------------------------

@router.get(
    "/overview",
    response_model=TicketAnalytics,
    summary="Ticket analytics overview",
    description="""
Return aggregate metrics for the authenticated user's tickets:

- `total_tickets`
- `open_tickets`
- `resolved_tickets`
- `tickets_by_priority` (low/medium/high/critical + unclassified)
- `tickets_by_sentiment` (positive/neutral/negative + unclassified)

All counts are computed in the database and scoped to the current user.

**Authentication:** Bearer token required.
""",
)
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketAnalytics:
    """Return the full analytics overview for the authenticated user."""
    logger.info("Analytics overview request: user_id=%s", current_user.id)
    return await analytics_service.get_ticket_analytics(
        db=db,
        owner_id=current_user.id,
    )


# ---------------------------------------------------------------------------
# GET /analytics/sentiment — sentiment breakdown
# ---------------------------------------------------------------------------

@router.get(
    "/sentiment",
    response_model=dict[str, int],
    summary="Tickets grouped by sentiment",
    description="""
Return the count of the authenticated user's tickets grouped by AI-detected
sentiment. Every key is always present (defaulting to 0):

`positive`, `neutral`, `negative`, `unclassified`

`unclassified` covers tickets the AI has not yet analysed.

**Authentication:** Bearer token required.
""",
)
async def analytics_sentiment(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> dict[str, int]:
    """Return the sentiment breakdown for the authenticated user."""
    logger.info("Analytics sentiment request: user_id=%s", current_user.id)
    analytics = await analytics_service.get_ticket_analytics(
        db=db,
        owner_id=current_user.id,
    )
    return analytics.tickets_by_sentiment


# ---------------------------------------------------------------------------
# GET /analytics/priorities — priority breakdown
# ---------------------------------------------------------------------------

@router.get(
    "/priorities",
    response_model=dict[str, int],
    summary="Tickets grouped by priority",
    description="""
Return the count of the authenticated user's tickets grouped by priority.
Every key is always present (defaulting to 0):

`low`, `medium`, `high`, `critical`, `unclassified`

`unclassified` covers tickets the AI has not yet prioritised.

**Authentication:** Bearer token required.
""",
)
async def analytics_priorities(
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> dict[str, int]:
    """Return the priority breakdown for the authenticated user."""
    logger.info("Analytics priorities request: user_id=%s", current_user.id)
    analytics = await analytics_service.get_ticket_analytics(
        db=db,
        owner_id=current_user.id,
    )
    return analytics.tickets_by_priority
