"""
schemas/user.py — Pydantic v2 schemas for User authentication.

Schemas defined here:
  UserCreate      — payload for POST /api/v1/auth/register
  UserLogin       — payload for POST /api/v1/auth/login
  UserResponse    — safe public representation (never exposes password)
  TokenResponse   — JWT token pair returned after login / register
  TokenPayload    — decoded JWT claims used internally by dependencies

Validation rules enforced at the schema layer (before any DB call):
  - email   : valid format, lowercase-normalised, max 255 chars
  - password: min 8 chars, must contain uppercase, lowercase, and digit
  - username: 3–50 chars, alphanumeric + underscore only
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_PASSWORD_MIN_LENGTH = 8

def _validate_password_strength(password: str) -> str:
    """
    Enforce password rules:
      - At least 8 characters
      - At least one uppercase letter  (A-Z)
      - At least one lowercase letter  (a-z)
      - At least one digit             (0-9)

    Special characters are allowed but not required.
    Raises ValueError with a user-friendly message on failure.
    """
    errors: list[str] = []

    if len(password) < _PASSWORD_MIN_LENGTH:
        errors.append(f"at least {_PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        errors.append("at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("at least one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("at least one digit")

    if errors:
        raise ValueError("Password must contain " + ", ".join(errors) + ".")

    return password


def _normalise_email(email: str) -> str:
    """Lowercase and strip whitespace so 'User@Example.COM' == 'user@example.com'."""
    return email.strip().lower()


def _validate_username(username: str) -> str:
    """Only allow alphanumeric characters and underscores."""
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        raise ValueError(
            "Username may only contain letters, numbers, and underscores."
        )
    return username.strip()


# ---------------------------------------------------------------------------
# UserCreate — registration payload
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    """
    Validated payload for POST /api/v1/auth/register.

    Example request body:
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "Secure123",
            "confirm_password": "Secure123"
        }
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Unique display name. Letters, numbers, and underscores only.",
        examples=["john_doe"],
    )

    email: EmailStr = Field(
        ...,
        max_length=255,
        description="Valid email address. Stored in lowercase.",
        examples=["john@example.com"],
    )

    password: str = Field(
        ...,
        min_length=_PASSWORD_MIN_LENGTH,
        max_length=128,
        description=(
            "Must be at least 8 characters and contain "
            "an uppercase letter, a lowercase letter, and a digit."
        ),
        examples=["Secure123"],
    )

    confirm_password: str = Field(
        ...,
        description="Must exactly match the password field.",
        examples=["Secure123"],
    )

    # ── Field-level validators ─────────────────────────────────────────────

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        return _validate_username(value)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return _normalise_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_password_strength(value)

    # ── Cross-field validator ──────────────────────────────────────────────

    @model_validator(mode="after")
    def passwords_match(self) -> "UserCreate":
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match.")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "password": "Secure123",
                "confirm_password": "Secure123",
            }
        }
    )


# ---------------------------------------------------------------------------
# UserLogin — login payload
# ---------------------------------------------------------------------------

class UserLogin(BaseModel):
    """
    Validated payload for POST /api/v1/auth/login.

    Accepts email + password only. Username login is intentionally
    not supported here to keep the auth surface simple.

    Example request body:
        {
            "email": "john@example.com",
            "password": "Secure123"
        }
    """

    email: EmailStr = Field(
        ...,
        max_length=255,
        description="Registered email address.",
        examples=["john@example.com"],
    )

    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Account password.",
        examples=["Secure123"],
    )

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return _normalise_email(value)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "john@example.com",
                "password": "Secure123",
            }
        }
    )


# ---------------------------------------------------------------------------
# UserResponse — safe public representation
# ---------------------------------------------------------------------------

class UserResponse(BaseModel):
    """
    Shape of a User object returned by the API.

    NEVER includes hashed_password or any internal fields.
    `from_attributes=True` allows building this from a SQLAlchemy ORM object
    directly: UserResponse.model_validate(user_orm_object)
    """

    id: uuid.UUID = Field(description="Unique user identifier.")
    username: str  = Field(description="Display name.")
    email: str     = Field(description="Email address.")
    is_active: bool = Field(description="Whether the account is active.")
    role: str      = Field(description="User role: 'user' | 'admin' | 'support'.")
    created_at: datetime = Field(description="Account creation timestamp (UTC).")
    updated_at: datetime = Field(description="Last update timestamp (UTC).")

    model_config = ConfigDict(
        from_attributes=True,       # enables ORM-mode: model_validate(orm_obj)
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "username": "john_doe",
                "email": "john@example.com",
                "is_active": True,
                "role": "user",
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
            }
        },
    )


# ---------------------------------------------------------------------------
# TokenResponse — returned after successful login / register
# ---------------------------------------------------------------------------

class TokenResponse(BaseModel):
    """
    JWT token pair returned by /login and /register.

    access_token  — short-lived (30 min default), sent in Authorization header.
    refresh_token — longer-lived (7 days default), used to obtain a new access token.
    token_type    — always "bearer" per OAuth2 spec.
    """

    access_token: str  = Field(description="Short-lived JWT access token.")
    refresh_token: str = Field(description="Long-lived JWT refresh token.")
    token_type: str    = Field(default="bearer", description="Token scheme.")
    user: UserResponse = Field(description="The authenticated user's public profile.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "user": {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "username": "john_doe",
                    "email": "john@example.com",
                    "is_active": True,
                    "role": "user",
                    "created_at": "2024-01-15T10:30:00Z",
                    "updated_at": "2024-01-15T10:30:00Z",
                },
            }
        }
    )


# ---------------------------------------------------------------------------
# RefreshRequest — payload for POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------

class RefreshRequest(BaseModel):
    """Payload for POST /api/v1/auth/refresh — exchange a refresh token."""

    refresh_token: str = Field(
        ...,
        description="A valid, unexpired refresh token.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    )


# ---------------------------------------------------------------------------
# TokenPayload — decoded JWT claims (internal use only)
# ---------------------------------------------------------------------------

class TokenPayload(BaseModel):
    """
    Shape of the decoded JWT payload.

    Used by core/dependencies.py to extract the current user from a token.
    Never returned to the client — internal only.

    Standard JWT claims used:
      sub  — subject (user UUID as string)
      exp  — expiry timestamp (handled by python-jose)
      type — "access" or "refresh" to prevent token-type confusion attacks
    """

    sub: str = Field(description="User UUID as a string.")
    type: str = Field(description="Token type: 'access' or 'refresh'.")