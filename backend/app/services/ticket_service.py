"""
services/ticket_service.py — Business logic for Ticket CRUD + AI enrichment.

After create_ticket() persists the ticket, it fires enrich_ticket() from
ai_service.py to populate ai_summary, sentiment, and priority asynchronously
within the same request context.
"""

from __future__ import annotations

import logging
import math
import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

async def _get_ticket_or_404(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> Ticket:
    """
    Fetch a ticket by ID scoped to owner_id, or raise HTTP 404.
    Returns 404 for both 'not found' and 'wrong owner' (IDOR prevention).
    """
    result = await db.execute(
        select(Ticket).where(
            Ticket.id == ticket_id,
            Ticket.owner_id == owner_id,
        )
    )
    ticket = result.scalars().first()

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found.",
        )

    return ticket


# ---------------------------------------------------------------------------
# Create  (with AI enrichment)
# ---------------------------------------------------------------------------

async def create_ticket(
    db: AsyncSession,
    payload: TicketCreate,
    owner_id: uuid.UUID,
) -> TicketResponse:
    """
    Persist a new ticket then enrich it with AI analysis.

    Steps:
      1. INSERT the ticket with status=open, AI fields=None
      2. Flush to get ticket.id without committing
      3. Fire AI enrichment — analyses title+description, writes
         ai_summary, sentiment, priority back to the same row
      4. Refresh the ORM object so returned data includes AI fields
      5. Return the fully enriched TicketResponse

    AI enrichment is best-effort: if OpenAI is unavailable, the ticket
    is returned with null AI fields rather than failing the request.
    """
    # ── 1. Persist the ticket ──────────────────────────────────────────────
    ticket = Ticket(
        title=payload.title,
        description=payload.description,
        status=payload.status.value,
        owner_id=owner_id,
        priority=None,
        ai_summary=None,
        sentiment=None,
    )

    db.add(ticket)
    await db.flush()

    logger.info(
        "Ticket created: id=%s title=%r owner_id=%s",
        ticket.id, ticket.title, owner_id,
    )

    # ── 2. AI enrichment ───────────────────────────────────────────────────
    # Import here to avoid circular imports at module load time
    from app.services import ai_service

    await ai_service.enrich_ticket(
        db=db,
        ticket_id=ticket.id,
        owner_id=owner_id,
        title=ticket.title,
        description=ticket.description,
    )

    # ── 3. Refresh to pick up AI fields written by enrich_ticket ──────────
    await db.refresh(ticket)

    return TicketResponse.model_validate(ticket)


# ---------------------------------------------------------------------------
# Read — single ticket
# ---------------------------------------------------------------------------

async def get_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> TicketResponse:
    """Fetch a single ticket scoped to the requesting user."""
    ticket = await _get_ticket_or_404(db, ticket_id, owner_id)
    return TicketResponse.model_validate(ticket)


# ---------------------------------------------------------------------------
# Read — paginated list
# ---------------------------------------------------------------------------

async def get_user_tickets(
    db: AsyncSession,
    owner_id: uuid.UUID,
    page: int = 1,
    size: int = 10,
) -> TicketListResponse:
    """Return a paginated list of tickets owned by owner_id (newest first)."""
    page = max(1, page)
    size = max(1, min(size, 100))
    offset = (page - 1) * size

    count_result = await db.execute(
        select(func.count()).where(Ticket.owner_id == owner_id)
    )
    total: int = count_result.scalar_one()

    tickets_result = await db.execute(
        select(Ticket)
        .where(Ticket.owner_id == owner_id)
        .order_by(Ticket.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    tickets = tickets_result.scalars().all()

    pages = math.ceil(total / size) if total > 0 else 1

    return TicketListResponse(
        items=[TicketResponse.model_validate(t) for t in tickets],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


# ---------------------------------------------------------------------------
# Update  (PATCH — partial)
# ---------------------------------------------------------------------------

async def update_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    owner_id: uuid.UUID,
) -> TicketResponse:
    """
    Partially update a ticket. Only fields explicitly provided are changed.
    Used by both user PATCH requests and the AI enrichment pipeline.
    """
    ticket = await _get_ticket_or_404(db, ticket_id, owner_id)

    updates = payload.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No updatable fields provided.",
        )

    for field, value in updates.items():
        setattr(ticket, field, value.value if hasattr(value, "value") else value)

    await db.flush()
    await db.refresh(ticket)

    logger.info(
        "Ticket updated: id=%s fields=%s owner_id=%s",
        ticket.id, list(updates.keys()), owner_id,
    )

    return TicketResponse.model_validate(ticket)


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------

async def delete_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    owner_id: uuid.UUID,
) -> None:
    """Permanently delete a ticket. Only the owner may delete their ticket."""
    ticket = await _get_ticket_or_404(db, ticket_id, owner_id)
    await db.delete(ticket)
    await db.flush()
    logger.info("Ticket deleted: id=%s owner_id=%s", ticket_id, owner_id)