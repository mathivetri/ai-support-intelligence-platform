"""
models/ticket.py — SQLAlchemy ORM model for the Ticket entity.

Table: tickets

Columns:
  id           UUID primary key
  title        Short summary of the issue
  description  Full detail of the issue
  status       Lifecycle state  : open | in_progress | resolved | closed
  priority     Urgency level    : low | medium | high | critical
  ai_summary   OpenAI-generated summary of the ticket content
  sentiment    AI-detected sentiment : positive | neutral | negative
  owner_id     FK → users.id (the user who created the ticket)
  created_at   Set on INSERT by DB    ← TimestampMixin
  updated_at   Refreshed on UPDATE    ← TimestampMixin

Relationships:
  owner        Many-to-one → User (each ticket belongs to one user)
"""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


# ---------------------------------------------------------------------------
# Enums — enforced at the Python layer
# ---------------------------------------------------------------------------
# Using Python enums (not PostgreSQL ENUM types) keeps migrations simpler:
# adding a new value only requires a code change, not an ALTER TYPE statement.
# SQLAlchemy stores these as VARCHAR in the DB.

class TicketStatus(str, enum.Enum):
    """Lifecycle states of a support ticket."""
    OPEN        = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED    = "resolved"
    CLOSED      = "closed"


class TicketPriority(str, enum.Enum):
    """Urgency levels assigned to a ticket."""
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class TicketSentiment(str, enum.Enum):
    """Sentiment detected by the AI service."""
    POSITIVE = "positive"
    NEUTRAL  = "neutral"
    NEGATIVE = "negative"


# ---------------------------------------------------------------------------
# Ticket model
# ---------------------------------------------------------------------------

class Ticket(TimestampMixin, Base):
    """
    Represents a support ticket submitted by a user.

    AI fields (ai_summary, sentiment, priority) start as None and are
    populated asynchronously by the AI service after ticket creation.
    """

    __tablename__ = "tickets"

    # ── Primary key ────────────────────────────────────────────────────────

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        nullable=False,
        comment="Globally unique ticket identifier.",
    )

    # ── Core fields ────────────────────────────────────────────────────────

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Short summary of the issue (max 255 chars).",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full description of the issue supplied by the user.",
    )

    # ── Status & priority ──────────────────────────────────────────────────
    # Stored as VARCHAR; the Python enum validates values before they hit the DB.
    # server_default ensures rows inserted via raw SQL also get safe defaults.

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TicketStatus.OPEN.value,
        server_default=text("'open'"),
        index=True,
        comment="Ticket lifecycle state: open | in_progress | resolved | closed.",
    )

    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=True,                      # nullable: AI classifies after creation
        default=None,
        comment="Urgency level: low | medium | high | critical. Set by AI service.",
    )

    # ── AI-enriched fields ─────────────────────────────────────────────────
    # All three start as NULL and are written by ai_service.py after the
    # ticket is persisted. Keeping them nullable avoids blocking ticket
    # creation on AI availability.

    ai_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        comment="OpenAI-generated concise summary of the ticket.",
    )

    sentiment: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        default=None,
        comment="AI-detected sentiment: positive | neutral | negative.",
    )

    # ── Foreign key ────────────────────────────────────────────────────────

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="UUID of the user who created this ticket.",
    )

    # ── Relationships ──────────────────────────────────────────────────────
    # back_populates="tickets" matches the `tickets` attribute on the User model.
    # lazy="selectin" loads the owner automatically with an IN query —
    # safe for async SQLAlchemy (lazy="select" triggers lazy-loading which
    # is not supported in async contexts).

    owner: Mapped["User"] = relationship(       # type: ignore[name-defined]
        "User",
        back_populates="tickets",
        lazy="selectin",
    )

    # ── Helpers ────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"<Ticket id={self.id} title={self.title!r} "
            f"status={self.status!r} priority={self.priority!r}>"
        )

    def __str__(self) -> str:
        return self.title