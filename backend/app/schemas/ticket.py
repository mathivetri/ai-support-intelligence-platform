"""
schemas/ticket.py — Pydantic v2 schemas for Ticket CRUD and AI enrichment.

Schemas defined here:
  TicketStatus      — allowed status values    (mirrors models/ticket.py enum)
  TicketPriority    — allowed priority values  (mirrors models/ticket.py enum)
  TicketSentiment   — allowed sentiment values (mirrors models/ticket.py enum)
  TicketCreate      — payload for POST /api/v1/tickets
  TicketUpdate      — payload for PATCH /api/v1/tickets/{id}  (all fields optional)
  TicketResponse    — full public representation returned by the API
  TicketListResponse— paginated wrapper for GET /api/v1/tickets

Design rules:
  - Enums are re-declared here (not imported from models/) so the schema
    layer has no dependency on SQLAlchemy.  Both sets of enums share the
    same string values so they are always in sync.
  - TicketUpdate uses Optional fields with default=None so PATCH requests
    only update the fields that are actually provided.
  - TicketResponse uses from_attributes=True for direct ORM-to-schema conversion.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TicketStatus(str, enum.Enum):
    """
    Lifecycle state of a support ticket.
    String enum so JSON serialisation works without extra config.
    """
    OPEN        = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED    = "resolved"
    CLOSED      = "closed"


class TicketPriority(str, enum.Enum):
    """
    Urgency level of a support ticket.
    Assigned by the AI service after ticket creation.
    """
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class TicketSentiment(str, enum.Enum):
    """
    Customer sentiment detected by the AI service.
    """
    POSITIVE = "positive"
    NEUTRAL  = "neutral"
    NEGATIVE = "negative"


# ---------------------------------------------------------------------------
# TicketCreate — POST /api/v1/tickets
# ---------------------------------------------------------------------------

class TicketCreate(BaseModel):
    """
    Validated payload for creating a new support ticket.

    Only title and description are required from the user.
    status defaults to "open"; all AI fields are populated later
    by the AI service and must not be supplied at creation time.

    Example request body:
        {
            "title": "Cannot log in to my account",
            "description": "I have been unable to log in since yesterday..."
        }
    """

    title: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Short summary of the issue (5–255 characters).",
        examples=["Cannot log in to my account"],
    )

    description: str = Field(
        ...,
        min_length=20,
        max_length=5000,
        description="Full description of the issue (20–5000 characters).",
        examples=["I have been unable to log in since yesterday evening..."],
    )

    # Status can optionally be set at creation (e.g. imported tickets)
    # but defaults to OPEN for all normal submissions.
    status: TicketStatus = Field(
        default=TicketStatus.OPEN,
        description="Initial lifecycle state. Defaults to 'open'.",
    )

    # ── Field validators ───────────────────────────────────────────────────

    @field_validator("title")
    @classmethod
    def sanitise_title(cls, value: str) -> str:
        """Strip leading/trailing whitespace and collapse internal runs."""
        return " ".join(value.strip().split())

    @field_validator("description")
    @classmethod
    def sanitise_description(cls, value: str) -> str:
        """Strip leading/trailing whitespace only — preserve internal formatting."""
        return value.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Cannot log in to my account",
                "description": (
                    "I have been unable to log in since yesterday evening. "
                    "I receive an 'Invalid credentials' error even though "
                    "I am sure my password is correct. I have tried resetting "
                    "it twice but the problem persists."
                ),
                "status": "open",
            }
        }
    )


# ---------------------------------------------------------------------------
# TicketUpdate — PATCH /api/v1/tickets/{ticket_id}
# ---------------------------------------------------------------------------

class TicketUpdate(BaseModel):
    """
    Validated payload for partially updating an existing ticket.

    All fields are Optional — a PATCH request only updates the fields
    that are explicitly included in the request body.  Fields omitted
    from the payload are left unchanged in the database.

    AI fields (ai_summary, sentiment, priority) can be updated here
    to allow manual overrides by support agents, or programmatic
    updates from the AI service.

    Example request body (update status only):
        { "status": "in_progress" }

    Example request body (full update):
        {
            "title": "Updated title",
            "status": "resolved",
            "priority": "high"
        }
    """

    title: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=255,
        description="Updated ticket title.",
    )

    description: Optional[str] = Field(
        default=None,
        min_length=20,
        max_length=5000,
        description="Updated ticket description.",
    )

    status: Optional[TicketStatus] = Field(
        default=None,
        description="Updated lifecycle state.",
    )

    priority: Optional[TicketPriority] = Field(
        default=None,
        description="Updated priority level.",
    )

    ai_summary: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="AI-generated summary (set by AI service or manual override).",
    )

    sentiment: Optional[TicketSentiment] = Field(
        default=None,
        description="AI-detected sentiment (set by AI service or manual override).",
    )

    # ── Field validators ───────────────────────────────────────────────────

    @field_validator("title")
    @classmethod
    def sanitise_title(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return " ".join(value.strip().split())

    @field_validator("description")
    @classmethod
    def sanitise_description(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "in_progress",
                "priority": "high",
            }
        }
    )


# ---------------------------------------------------------------------------
# TicketResponse — returned by all ticket endpoints
# ---------------------------------------------------------------------------

class TicketResponse(BaseModel):
    """
    Full public representation of a ticket returned by the API.

    Built directly from a SQLAlchemy Ticket ORM object via:
        TicketResponse.model_validate(ticket_orm_object)

    AI fields (ai_summary, sentiment, priority) are None until the
    AI service processes the ticket — clients must handle null values.
    """

    id: uuid.UUID = Field(description="Unique ticket identifier.")

    title: str       = Field(description="Short summary of the issue.")
    description: str = Field(description="Full description of the issue.")

    status: TicketStatus = Field(description="Current lifecycle state.")

    priority: Optional[TicketPriority] = Field(
        default=None,
        description="Urgency level. None until classified by AI.",
    )

    ai_summary: Optional[str] = Field(
        default=None,
        description="AI-generated summary. None until processed.",
    )

    sentiment: Optional[TicketSentiment] = Field(
        default=None,
        description="AI-detected sentiment. None until processed.",
    )

    owner_id: uuid.UUID = Field(description="UUID of the user who created this ticket.")

    created_at: datetime = Field(description="Ticket creation timestamp (UTC).")
    updated_at: datetime = Field(description="Last update timestamp (UTC).")

    model_config = ConfigDict(
        from_attributes=True,           # enables model_validate(orm_object)
        use_enum_values=True,           # serialise enums as their string value
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
                "title": "Cannot log in to my account",
                "description": "I have been unable to log in since yesterday...",
                "status": "open",
                "priority": "high",
                "ai_summary": "User is experiencing login issues since yesterday.",
                "sentiment": "negative",
                "owner_id": "0d6d2300-c0b7-4b17-8503-1851d35bb79f",
                "created_at": "2026-06-03T06:52:48Z",
                "updated_at": "2026-06-03T06:52:48Z",
            }
        },
    )


# ---------------------------------------------------------------------------
# TicketListResponse — paginated wrapper for GET /api/v1/tickets
# ---------------------------------------------------------------------------

class TicketListResponse(BaseModel):
    """
    Paginated list of tickets returned by GET /api/v1/tickets.

    Clients use `total`, `page`, and `size` to implement pagination controls.

    Example response:
        {
            "items": [...],
            "total": 42,
            "page":  1,
            "size":  10,
            "pages": 5
        }
    """

    items: list[TicketResponse] = Field(description="Tickets for the current page.")
    total: int                  = Field(description="Total number of matching tickets.")
    page:  int                  = Field(description="Current page number (1-based).")
    size:  int                  = Field(description="Number of items per page.")
    pages: int                  = Field(description="Total number of pages.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [],
                "total": 42,
                "page":  1,
                "size":  10,
                "pages": 5,
            }
        }
    )