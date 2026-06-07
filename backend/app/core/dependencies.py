"""
core/dependencies.py — Reusable FastAPI dependencies.

Provides:
  get_current_user   — decodes the Bearer token and returns the active user
  get_current_admin  — same as above but enforces role == "admin"

Usage in any protected route:
    from app.core.dependencies import get_current_user
    from app.schemas.user import UserResponse

    @router.get("/me")
    async def get_me(current_user: UserResponse = Depends(get_current_user)):
        return current_user

How it works per request:
  1. OAuth2PasswordBearer extracts the raw token from "Authorization: Bearer <token>"
  2. decode_access_token() verifies the signature, expiry, and token type
  3. get_user_by_id() confirms the user still exists and is_active in the DB
  4. The UserResponse is injected into the route handler

Any failure at steps 1–3 raises HTTP 401 before the route handler runs.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.schemas.user import UserResponse
from app.services import auth_service

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OAuth2PasswordBearer
# ---------------------------------------------------------------------------

# tokenUrl tells Swagger UI where to send the username/password form to get
# a token — it powers the "Authorize" button in /docs.
# auto_error=True (default) automatically raises HTTP 401 when the
# Authorization header is missing entirely.

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login/form",
    scheme_name="JWT",
    description="Paste your **access_token** from /register or /login.",
    auto_error=True,
)


# ---------------------------------------------------------------------------
# get_current_user
# ---------------------------------------------------------------------------

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Decode the Bearer token and return the authenticated user.

    Injected via Depends() into any route that requires authentication.

    Steps:
      1. OAuth2PasswordBearer extracts the raw JWT string from the header.
         Raises HTTP 401 automatically if the header is absent.
      2. decode_access_token() validates signature, expiry, and token type.
         Raises HTTP 401 if the token is invalid or expired.
      3. The "sub" claim (user UUID) is extracted from the token payload.
         Raises HTTP 401 if "sub" is missing or not a valid UUID.
      4. auth_service.get_user_by_id() fetches the user from the DB and
         confirms is_active == True.
         Raises HTTP 401 if the user no longer exists or is deactivated.

    Args:
        token: Raw JWT string injected by OAuth2PasswordBearer.
        db:    Async DB session injected by get_db.

    Returns:
        UserResponse — safe public fields only (no hashed_password).

    Raises:
        HTTP 401 at any step above.
    """

    # ── Step 1: Decode and validate the access token ───────────────────────
    # decode_access_token raises HTTP 401 if:
    #   - signature is invalid
    #   - token is expired
    #   - token type is not "access" (blocks refresh tokens on resource routes)
    payload = decode_access_token(token)

    # ── Step 2: Extract and validate the user UUID from "sub" ──────────────
    try:
        user_id = uuid.UUID(payload.sub)
    except (ValueError, AttributeError):
        logger.warning("Invalid UUID in token sub claim: %s", payload.sub)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # ── Step 3: Fetch user from DB and confirm they are still active ────────
    # This step is critical: a valid token for a deleted or deactivated user
    # must be rejected. Tokens are not revocable, but this DB check ensures
    # deactivated users can't access the API even with a non-expired token.
    user = await auth_service.get_user_by_id(db, user_id)

    logger.debug("Authenticated user: id=%s username=%s", user.id, user.username)

    return user


# ---------------------------------------------------------------------------
# get_current_admin
# ---------------------------------------------------------------------------

async def get_current_admin(
    current_user: UserResponse = Depends(get_current_user),
) -> UserResponse:
    """
    Extend get_current_user with an admin role check.

    Use this dependency on any route that requires elevated privileges
    (e.g. user management, system configuration).

    Args:
        current_user: Injected by get_current_user — already authenticated.

    Returns:
        The same UserResponse if the user has role == "admin".

    Raises:
        HTTP 403 Forbidden if the user is authenticated but not an admin.

    Usage:
        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: uuid.UUID,
            admin: UserResponse = Depends(get_current_admin),
        ):
            ...
    """
    if current_user.role != "admin":
        logger.warning(
            "Forbidden: user id=%s role=%s attempted admin action",
            current_user.id,
            current_user.role,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to perform this action.",
        )

    return current_user