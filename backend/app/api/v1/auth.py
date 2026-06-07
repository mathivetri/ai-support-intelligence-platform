"""
api/v1/auth.py — Authentication route handlers.

Endpoints:
  POST /api/v1/auth/register      Create account, return JWT token pair
  POST /api/v1/auth/login         JSON login, return JWT token pair
  POST /api/v1/auth/login/form    OAuth2 form login for Swagger UI Authorize button
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.user import TokenResponse, UserCreate, UserLogin
from app.services import auth_service

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="""
Create a new user account and receive a JWT token pair immediately.

**Validation rules:**
- `username`: 3–50 characters, letters/numbers/underscores only
- `email`: valid format, stored as lowercase
- `password`: minimum 8 characters, must include uppercase, lowercase, and a digit
- `confirm_password`: must exactly match `password`

**On success:** returns `201 Created` with `access_token`, `refresh_token`, and the new user's public profile.

**On conflict:** returns `409 Conflict` if the email or username is already registered.
    """,
    responses={
        201: {"description": "Account created — token pair returned."},
        409: {"description": "Email or username already registered."},
        422: {"description": "Validation error — check request body."},
    },
)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    logger.info("Register request for username=%s email=%s", payload.username, payload.email)
    return await auth_service.register(db, payload)


# ---------------------------------------------------------------------------
# POST /login  (JSON body — for API clients and direct calls)
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description="""
Authenticate with an existing account and receive a JWT token pair.

**Request body:**
- `email`: registered email address
- `password`: account password

**On success:** returns `200 OK` with `access_token`, `refresh_token`, and the user's public profile.

**On failure:** returns `401 Unauthorized`.
**On disabled account:** returns `403 Forbidden`.
    """,
    responses={
        200: {"description": "Login successful — token pair returned."},
        401: {"description": "Incorrect email or password."},
        403: {"description": "Account has been deactivated."},
        422: {"description": "Validation error — check request body."},
    },
)
async def login(
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    logger.info("Login request for email=%s", payload.email)
    return await auth_service.login(db, payload)


# ---------------------------------------------------------------------------
# POST /login/form  (OAuth2 form — for Swagger UI Authorize button)
# ---------------------------------------------------------------------------

@router.post(
    "/login/form",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login (Swagger UI)",
    description="""
OAuth2 password flow endpoint used by the **Swagger UI Authorize button**.

Enter your email in the `username` field and your password in `password`.
Leave `client_id` and `client_secret` empty.

This endpoint accepts `application/x-www-form-urlencoded` (not JSON).
Use `POST /login` for JSON-based API clients.
    """,
)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Swagger UI Authorize button calls this endpoint with form data.
    The 'username' field must contain the email address.
    """
    logger.info("Form login request for email=%s", form_data.username)
    payload = UserLogin(email=form_data.username, password=form_data.password)
    return await auth_service.login(db, payload)