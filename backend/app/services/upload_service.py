"""
services/upload_service.py — optional ticket screenshot uploads via Cloudinary.

Design:
  - If Cloudinary is not configured, uploads are skipped (returns None) so the
    feature degrades gracefully rather than breaking ticket creation.
  - Client-side problems (wrong file type, too large) raise HTTP errors so the
    user can fix and retry.
  - Provider-side failures (Cloudinary down) are logged and treated as "no
    screenshot" — the ticket is still created with its text content.

Public API:
  upload_ticket_screenshot(file) -> str | None   (the secure CDN URL, or None)
"""

from __future__ import annotations

import logging

import cloudinary
import cloudinary.uploader
from fastapi import HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)

_ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/webp",
    "image/gif",
}
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB

_configured = False


def _ensure_configured() -> None:
    """Configure the Cloudinary SDK once per process."""
    global _configured
    if not _configured:
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True,
        )
        _configured = True


async def upload_ticket_screenshot(file: UploadFile) -> str | None:
    """
    Upload a ticket screenshot to Cloudinary and return its secure URL.

    Returns None if Cloudinary is not configured, the file is empty, or the
    provider upload fails. Raises HTTP 415/413 for invalid client input.
    """
    # No file actually provided.
    if file is None or not file.filename:
        return None

    # Feature disabled — skip silently.
    if not settings.cloudinary_enabled:
        logger.warning("Cloudinary not configured — skipping screenshot upload.")
        return None

    # ── Validate type (client error → block) ───────────────────────────────
    if file.content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported image type. Use PNG, JPEG, WEBP, or GIF.",
        )

    data = await file.read()
    if not data:
        return None

    # ── Validate size (client error → block) ───────────────────────────────
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image too large. Maximum size is 5 MB.",
        )

    # ── Upload (provider error → degrade) ──────────────────────────────────
    _ensure_configured()
    try:
        # The Cloudinary SDK is synchronous; run it off the event loop.
        result = await run_in_threadpool(
            cloudinary.uploader.upload,
            data,
            folder="ticket_screenshots",
            resource_type="image",
        )
    except Exception as exc:  # noqa: BLE001 — degrade on any provider failure
        logger.error("Cloudinary upload failed: %s. Ticket saved without screenshot.", exc)
        return None

    url = result.get("secure_url")
    logger.info("Screenshot uploaded: %s", url)
    return url
