"""
services/auth_service.py — Business logic for user authentication.

Responsibilities:
  - Register a new user (validate uniqueness, hash password, persist)
  - Authenticate an existing user (verify credentials, issue tokens)
  - Duplicate-check helpers for email and username

This layer sits between the API router and the database.
It never touches HTTP request/response objects directly —
all input arrives as validated Pydantic schemas and all output
is either an ORM model or a plain dict.

Dependency chain:
  api/v1/auth.py
    └── auth_service.register() / auth_service.login()
          ├── _get_user_by_email()       (async DB query)
          ├── _get_user_by_username()    (async DB query)
          ├── security.hash_password()   (pure function)
          ├── security.verify_password() (pure function)
          └── security.create_token_pair() (pure function)
"""

from __future__ import annotations

import logging
import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_token_pair,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Private DB helpers
# ---------------------------------------------------------------------------

async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """
    Return the User row whose email matches, or None.

    Email is already lowercased by the Pydantic schema validator before
    reaching this function, so no further normalisation is needed here.
    """
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalars().first()


async def _get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """Return the User row whose username matches, or None."""
    result = await db.execute(
        select(User).where(User.username == username)
    )
    return result.scalars().first()


async def _get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Return the User row by primary key, or None."""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalars().first()


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

async def register(db: AsyncSession, payload: UserCreate) -> TokenResponse:
    """
    Register a new user account and return a JWT token pair.

    Steps:
      1. Check the email is not already registered   → HTTP 409
      2. Check the username is not already taken     → HTTP 409
      3. Hash the plain-text password
      4. Persist the new User row
      5. Issue and return an access + refresh token pair

    Args:
        db:      Async SQLAlchemy session (injected via Depends(get_db)).
        payload: Validated UserCreate schema — email already lowercased,
                 passwords already confirmed to match.

    Returns:
        TokenResponse containing access_token, refresh_token, and
        the new user's public profile.

    Raises:
        HTTP 409 if the email or username is already registered.
    """

    # ── 1. Uniqueness checks ───────────────────────────────────────────────
    if await _get_user_by_email(db, payload.email):
        logger.warning("Registration attempt with existing email: %s", payload.email)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists.",
        )

    if await _get_user_by_username(db, payload.username):
        logger.warning(
            "Registration attempt with existing username: %s", payload.username
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken.",
        )

    # ── 2. Hash password ───────────────────────────────────────────────────
    # The plain-text password is never stored or logged.
    hashed = hash_password(payload.password)

    # ── 3. Persist the new user ────────────────────────────────────────────
    new_user = User(
        username=payload.username,
        email=payload.email,          # already lowercased by schema validator
        hashed_password=hashed,
        is_active=True,
        role="user",
    )

    db.add(new_user)
    await db.flush()      # write to DB within the current transaction so
                          # new_user.id is populated before we use it below;
                          # the actual COMMIT happens in get_db after the
                          # route handler returns successfully.

    logger.info("New user registered: id=%s username=%s", new_user.id, new_user.username)

    # ── 4. Issue token pair ────────────────────────────────────────────────
    token_data = {"sub": str(new_user.id), "role": new_user.role}
    tokens = create_token_pair(token_data)

    return TokenResponse(
        **tokens,
        user=UserResponse.model_validate(new_user),
    )


async def login(db: AsyncSession, payload: UserLogin) -> TokenResponse:
    """
    Authenticate an existing user and return a JWT token pair.

    Steps:
      1. Look up the user by email                   → HTTP 401 if not found
      2. Check the account is active                 → HTTP 403 if disabled
      3. Verify the plain-text password              → HTTP 401 if wrong
      4. Issue and return an access + refresh token pair

    Args:
        db:      Async SQLAlchemy session (injected via Depends(get_db)).
        payload: Validated UserLogin schema — email already lowercased.

    Returns:
        TokenResponse containing access_token, refresh_token, and
        the user's public profile.

    Raises:
        HTTP 401 if the email is not registered or the password is wrong.
        HTTP 403 if the account has been deactivated.

    Security note:
        Steps 1 and 3 return the same HTTP 401 with the same message.
        This prevents user-enumeration attacks where an attacker could
        distinguish "email not found" from "wrong password" to discover
        which emails are registered.
    """

    # ── 1. Look up the user ────────────────────────────────────────────────
    user = await _get_user_by_email(db, payload.email)

    # Use a single generic error for both "not found" and "wrong password"
    # to prevent user enumeration.
    _invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        logger.warning("Login attempt for unregistered email: %s", payload.email)
        raise _invalid_credentials

    # ── 2. Check account is active ─────────────────────────────────────────
    if not user.is_active:
        logger.warning("Login attempt on disabled account: id=%s", user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact support.",
        )

    # ── 3. Verify password ─────────────────────────────────────────────────
    if not verify_password(payload.password, user.hashed_password):
        logger.warning("Failed login attempt for user: id=%s", user.id)
        raise _invalid_credentials

    logger.info("User logged in: id=%s username=%s", user.id, user.username)

    # ── 4. Issue token pair ────────────────────────────────────────────────
    token_data = {"sub": str(user.id), "role": user.role}
    tokens = create_token_pair(token_data)

    return TokenResponse(
        **tokens,
        user=UserResponse.model_validate(user),
    )


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> UserResponse:
    """
    Fetch a user's public profile by their UUID.

    Used by the get_current_user dependency after decoding a JWT to
    confirm the user still exists and is active.

    Args:
        db:      Async SQLAlchemy session.
        user_id: UUID extracted from the token's "sub" claim.

    Returns:
        UserResponse (safe public fields only).

    Raises:
        HTTP 401 if no matching active user is found.
    """
    user = await _get_user_by_id(db, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserResponse.model_validate(user)