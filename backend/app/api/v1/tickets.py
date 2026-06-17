"""
api/v1/tickets.py — Ticket route handlers.

Endpoints:
  POST   /api/v1/tickets                 Create a new ticket
  GET    /api/v1/tickets                 List current user's tickets (paginated)
  GET    /api/v1/tickets/{ticket_id}     Get a single ticket by ID
  PATCH  /api/v1/tickets/{ticket_id}     Partially update a ticket
  DELETE /api/v1/tickets/{ticket_id}     Delete a ticket

All endpoints require a valid JWT access token.
All read/write operations are scoped to the authenticated user's tickets only.

This module is intentionally thin:
  - Declares HTTP contract (method, path, status code, response schema)
  - Extracts validated inputs (FastAPI handles this automatically)
  - Delegates all business logic to ticket_service
  - Returns the service result directly
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.schemas.ticket import (
    TicketCreate,
    TicketListResponse,
    TicketResponse,
    TicketUpdate,
)
from app.schemas.user import UserResponse
from app.services import ticket_service, upload_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /tickets — Create a new ticket
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new support ticket",
    description="""
Submit a new support ticket. The ticket is created immediately with
status `open` and no AI fields. AI enrichment (summary, sentiment,
priority) is processed asynchronously after creation.

Sent as `multipart/form-data` so an optional screenshot can be attached.

**Fields:**
- `title`: 5–255 characters (required)
- `description`: 20–5000 characters (required)
- `screenshot`: optional image file (PNG/JPEG/WEBP/GIF, max 5 MB)

**Authentication:** Bearer token required.
    """,
    responses={
        201: {"description": "Ticket created successfully."},
        401: {"description": "Not authenticated."},
        413: {"description": "Screenshot too large (max 5 MB)."},
        415: {"description": "Unsupported screenshot type."},
        422: {"description": "Validation error — check the submitted fields."},
    },
)
async def create_ticket(
    title: str = Form(...),
    description: str = Form(...),
    screenshot: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    """
    Create a new support ticket owned by the authenticated user.

    Accepts multipart form data: the text fields plus an optional screenshot.
    The screenshot (if any) is uploaded to Cloudinary before the ticket is
    persisted; only its URL is stored on the ticket.
    """
    # Re-use the Pydantic schema to validate title/description rules.
    payload = TicketCreate(title=title, description=description)

    logger.info(
        "Create ticket request: user_id=%s title=%r has_screenshot=%s",
        current_user.id, payload.title, bool(screenshot and screenshot.filename),
    )

    screenshot_url = await upload_service.upload_ticket_screenshot(screenshot)

    return await ticket_service.create_ticket(
        db=db,
        payload=payload,
        owner_id=current_user.id,
        screenshot_url=screenshot_url,
    )


# ---------------------------------------------------------------------------
# GET /tickets — List current user's tickets (paginated)
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=TicketListResponse,
    status_code=status.HTTP_200_OK,
    summary="List my tickets",
    description="""
Retrieve a paginated list of tickets belonging to the authenticated user.

Results are ordered by `created_at` descending (newest first).

**Query parameters:**
- `page`: Page number, 1-based (default: 1)
- `size`: Items per page, 1–100 (default: 10)

**Authentication:** Bearer token required.
    """,
    responses={
        200: {"description": "Paginated list of tickets."},
        401: {"description": "Not authenticated."},
    },
)
async def list_tickets(
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    size: int = Query(default=10, ge=1, le=100, description="Items per page (max 100)."),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketListResponse:
    """
    Return all tickets owned by the authenticated user, paginated.
    """
    logger.debug(
        "List tickets request: user_id=%s page=%d size=%d",
        current_user.id, page, size,
    )
    return await ticket_service.get_user_tickets(
        db=db,
        owner_id=current_user.id,
        page=page,
        size=size,
    )


# ---------------------------------------------------------------------------
# GET /tickets/{ticket_id} — Get a single ticket
# ---------------------------------------------------------------------------

@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a ticket by ID",
    description="""
Retrieve a single ticket by its UUID.

Returns `404 Not Found` if the ticket does not exist **or** belongs
to a different user — this prevents leaking the existence of other
users' tickets (IDOR prevention).

**Authentication:** Bearer token required.
    """,
    responses={
        200: {"description": "Ticket found and returned."},
        401: {"description": "Not authenticated."},
        404: {"description": "Ticket not found."},
    },
)
async def get_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    """
    Fetch a single ticket scoped to the authenticated user.
    """
    logger.debug(
        "Get ticket request: user_id=%s ticket_id=%s",
        current_user.id, ticket_id,
    )
    return await ticket_service.get_ticket(
        db=db,
        ticket_id=ticket_id,
        owner_id=current_user.id,
    )


# ---------------------------------------------------------------------------
# PATCH /tickets/{ticket_id} — Partially update a ticket
# ---------------------------------------------------------------------------

@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a ticket",
    description="""
Partially update a ticket using PATCH semantics.

Only fields included in the request body are updated.
Omitted fields retain their current values.

**Updatable fields:**
- `title`, `description` — user-editable content
- `status` — lifecycle state: `open` | `in_progress` | `resolved` | `closed`
- `priority` — urgency: `low` | `medium` | `high` | `critical`
- `ai_summary` — AI-generated summary (can be manually overridden)
- `sentiment` — AI sentiment: `positive` | `neutral` | `negative`

**Ownership:** only the ticket owner can update their ticket.
Returns `404` if the ticket does not exist or belongs to another user.

**Authentication:** Bearer token required.
    """,
    responses={
        200: {"description": "Ticket updated successfully."},
        401: {"description": "Not authenticated."},
        404: {"description": "Ticket not found."},
        422: {"description": "Validation error or no updatable fields provided."},
    },
)
async def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    """
    Partially update a ticket owned by the authenticated user.
    """
    logger.info(
        "Update ticket request: user_id=%s ticket_id=%s",
        current_user.id, ticket_id,
    )
    return await ticket_service.update_ticket(
        db=db,
        ticket_id=ticket_id,
        payload=payload,
        owner_id=current_user.id,
    )


# ---------------------------------------------------------------------------
# DELETE /tickets/{ticket_id} — Delete a ticket
# ---------------------------------------------------------------------------

@router.delete(
    "/{ticket_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a ticket",
    description="""
Permanently delete a ticket.

Returns `204 No Content` on success — no response body.

**Ownership:** only the ticket owner can delete their ticket.
Returns `404` if the ticket does not exist or belongs to another user.

**Authentication:** Bearer token required.
    """,
    responses={
        204: {"description": "Ticket deleted successfully."},
        401: {"description": "Not authenticated."},
        404: {"description": "Ticket not found."},
    },
)
async def delete_ticket(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> None:
    """
    Permanently delete a ticket owned by the authenticated user.
    Returns HTTP 204 No Content on success.
    """
    logger.info(
        "Delete ticket request: user_id=%s ticket_id=%s",
        current_user.id, ticket_id,
    )
    await ticket_service.delete_ticket(
        db=db,
        ticket_id=ticket_id,
        owner_id=current_user.id,
    )


# ---------------------------------------------------------------------------
# PUT /tickets/{ticket_id}/screenshot — replace the attachment
# ---------------------------------------------------------------------------

@router.put(
    "/{ticket_id}/screenshot",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Replace a ticket's screenshot",
    description="""
Upload a new screenshot for an existing ticket (multipart/form-data).
Replaces any existing attachment.

**Authentication:** Bearer token required. Only the owner may update.
    """,
    responses={
        200: {"description": "Screenshot updated."},
        400: {"description": "Image could not be processed / uploads not configured."},
        401: {"description": "Not authenticated."},
        404: {"description": "Ticket not found."},
        413: {"description": "Screenshot too large (max 5 MB)."},
        415: {"description": "Unsupported screenshot type."},
    },
)
async def replace_screenshot(
    ticket_id: uuid.UUID,
    screenshot: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    """Upload and attach a new screenshot to a ticket owned by the user."""
    logger.info(
        "Replace screenshot request: user_id=%s ticket_id=%s",
        current_user.id, ticket_id,
    )
    url = await upload_service.upload_ticket_screenshot(screenshot)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not upload the image. Check the file or that uploads are configured.",
        )
    return await ticket_service.update_screenshot(
        db=db,
        ticket_id=ticket_id,
        owner_id=current_user.id,
        screenshot_url=url,
    )


# ---------------------------------------------------------------------------
# DELETE /tickets/{ticket_id}/screenshot — remove the attachment
# ---------------------------------------------------------------------------

@router.delete(
    "/{ticket_id}/screenshot",
    response_model=TicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove a ticket's screenshot",
    description="""
Detach the screenshot from a ticket (sets it to null). The image itself is
left in storage; only the link on the ticket is cleared.

**Authentication:** Bearer token required. Only the owner may update.
    """,
    responses={
        200: {"description": "Screenshot removed."},
        401: {"description": "Not authenticated."},
        404: {"description": "Ticket not found."},
    },
)
async def remove_screenshot(
    ticket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
) -> TicketResponse:
    """Clear the screenshot URL on a ticket owned by the user."""
    logger.info(
        "Remove screenshot request: user_id=%s ticket_id=%s",
        current_user.id, ticket_id,
    )
    return await ticket_service.update_screenshot(
        db=db,
        ticket_id=ticket_id,
        owner_id=current_user.id,
        screenshot_url=None,
    )