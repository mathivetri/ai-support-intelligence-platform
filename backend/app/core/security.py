"""
core/security.py — Password hashing and JWT token management.

Responsibilities:
  - Hash plain-text passwords with bcrypt via passlib
  - Verify a plain-text password against a stored hash
  - Create short-lived JWT access tokens
  - Create long-lived JWT refresh tokens
  - Decode and validate any JWT token
  - Raise consistent HTTP 401 errors on any auth failure

Public API (imported by services and dependencies):
  hash_password(plain)            -> str
  verify_password(plain, hashed)  -> bool
  create_access_token(data)       -> str
  create_refresh_token(data)      -> str
  create_token_pair(data)         -> dict[str, str]
  decode_token(token)             -> TokenPayload
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status

from app.core.config import settings
from app.schemas.user import TokenPayload


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

# CryptContext is the single place that controls which algorithm is used.
# bcrypt is the industry standard for password hashing:
#   - Adaptive cost factor (slow by design — resists brute force)
#   - Built-in salt (no manual salting required)
#   - "deprecated='auto'" automatically upgrades older hashes on next login
#     if you ever add a stronger scheme above bcrypt in the schemes list.

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(plain_password: str) -> str:
    """
    Return the bcrypt hash of `plain_password`.

    Call this once at registration and store the result.
    Never store or log the plain-text password.

    Args:
        plain_password: The raw password supplied by the user.

    Returns:
        A 60-character bcrypt hash string safe to store in the DB.
    """
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Return True if `plain_password` matches `hashed_password`.

    Uses a constant-time comparison internally to prevent timing attacks.
    Never compare hashes with == directly.

    Args:
        plain_password:  Raw password from the login request.
        hashed_password: bcrypt hash retrieved from the database.

    Returns:
        True if the password is correct, False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# JWT internals
# ---------------------------------------------------------------------------

# Centralise the credential exception so every auth failure returns
# the same HTTP 401 with the same WWW-Authenticate header.
# This prevents information leakage (attackers can't distinguish
# "token missing" from "token expired" from "token tampered").

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials.",
    headers={"WWW-Authenticate": "Bearer"},
)

_EXPIRED_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token has expired. Please log in again.",
    headers={"WWW-Authenticate": "Bearer"},
)


def _build_token(
    data: dict[str, Any],
    expires_delta: timedelta,
    token_type: str,
) -> str:
    """
    Internal helper — build and sign a JWT.

    Args:
        data:          Arbitrary claims to embed (must include "sub").
        expires_delta: How long until the token expires.
        token_type:    "access" or "refresh" — stored as claim "type".

    Returns:
        Signed JWT string.
    """
    now = datetime.now(timezone.utc)

    payload = {
        **data,                                     # caller-supplied claims
        "type": token_type,                         # token-type confusion guard
        "iat": now,                                 # issued-at
        "exp": now + expires_delta,                 # expiry
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# ---------------------------------------------------------------------------
# Public token creation API
# ---------------------------------------------------------------------------

def create_access_token(data: dict[str, Any]) -> str:
    """
    Create a short-lived JWT access token.

    Lifetime is controlled by ACCESS_TOKEN_EXPIRE_MINUTES in config.py.
    This token is sent in the Authorization: Bearer <token> header on
    every protected request.

    Args:
        data: Must contain "sub" (the user UUID as a string).
              May include additional claims (e.g. "role").

    Returns:
        Signed JWT access token string.

    Example:
        token = create_access_token({"sub": str(user.id), "role": user.role})
    """
    return _build_token(
        data=data,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a long-lived JWT refresh token.

    Lifetime is controlled by REFRESH_TOKEN_EXPIRE_DAYS in config.py.
    This token is used only to obtain a new access token via
    POST /api/v1/auth/refresh — it must NOT be accepted on resource endpoints.

    Args:
        data: Must contain "sub" (the user UUID as a string).

    Returns:
        Signed JWT refresh token string.
    """
    return _build_token(
        data=data,
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def create_token_pair(data: dict[str, Any]) -> dict[str, str]:
    """
    Create both an access token and a refresh token in one call.

    Use this in /register and /login route handlers so both tokens
    are always issued together with the same claims.

    Args:
        data: Must contain "sub" (the user UUID as a string).

    Returns:
        {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}

    Example:
        tokens = create_token_pair({"sub": str(user.id), "role": user.role})
        return TokenResponse(**tokens, user=UserResponse.model_validate(user))
    """
    return {
        "access_token":  create_access_token(data),
        "refresh_token": create_refresh_token(data),
        "token_type":    "bearer",
    }


# ---------------------------------------------------------------------------
# Token decoding and validation
# ---------------------------------------------------------------------------

def decode_token(token: str) -> TokenPayload:
    """
    Decode and validate a JWT token.

    Validates:
      - Signature    (was it signed with our SECRET_KEY?)
      - Expiry       (has the exp claim passed?)
      - Claims shape (does it have sub and type?)

    Args:
        token: Raw JWT string from the Authorization header.

    Returns:
        TokenPayload with `sub` (user UUID string) and `type`.

    Raises:
        HTTP 401 if the token is expired.
        HTTP 401 if the token is invalid for any other reason.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_aud": False},   # we don't use the audience claim
        )

        sub: str | None  = payload.get("sub")
        token_type: str | None = payload.get("type")

        if sub is None or token_type is None:
            raise _CREDENTIALS_EXCEPTION

        return TokenPayload(sub=sub, type=token_type)

    except jwt.ExpiredSignatureError:
        # Raised separately so the client gets a specific "expired" message
        # rather than a generic "invalid credentials" — helps frontend UX.
        raise _EXPIRED_EXCEPTION

    except JWTError:
        raise _CREDENTIALS_EXCEPTION


def decode_access_token(token: str) -> TokenPayload:
    """
    Decode a token and assert it is an access token.

    Use this in get_current_user dependency to block refresh tokens
    from being used on protected resource endpoints.

    Raises:
        HTTP 401 if the token is not an access token.
    """
    payload = decode_token(token)

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected an access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def decode_refresh_token(token: str) -> TokenPayload:
    """
    Decode a token and assert it is a refresh token.

    Use this in the /auth/refresh endpoint only.

    Raises:
        HTTP 401 if the token is not a refresh token.
    """
    payload = decode_token(token)

    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. Expected a refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload