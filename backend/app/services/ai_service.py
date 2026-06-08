"""
services/ai_service.py — OpenAI-powered ticket analysis.

Responsibilities:
  - Analyse a ticket's title and description using the OpenAI Chat API
  - Generate a concise plain-English summary
  - Classify customer sentiment   : positive | neutral | negative
  - Classify ticket priority      : low | medium | high | critical
  - Return a structured TicketAIResult dataclass
  - Persist the results back to the ticket via ticket_service.update_ticket()

Design principles:
  - Async throughout — never blocks the event loop
  - Structured JSON output via OpenAI's response_format  — no regex parsing
  - Graceful degradation — if OpenAI is unavailable, the ticket is saved
    without AI fields rather than failing the entire request
  - Retry with exponential backoff on transient API errors
  - All OpenAI calls are wrapped in try/except so a billing/quota issue
    never brings down the ticket creation endpoint

Public API:
  analyse_ticket(title, description)  -> TicketAIResult
  enrich_ticket(db, ticket_id, owner_id, title, description) -> None
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from typing import Optional

from openai import AsyncOpenAI, APIError, APITimeoutError, RateLimitError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.schemas.ticket import TicketSentiment, TicketPriority, TicketUpdate

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OpenAI client  (module-level singleton — one client per process)
# ---------------------------------------------------------------------------

_client = AsyncOpenAI(
    api_key=settings.GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1",
    timeout=30.0,
    max_retries=2,
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class TicketAIResult:
    """
    Structured output from the AI analysis.

    All fields are Optional — if OpenAI returns an unexpected value or the
    call fails entirely, the field stays None and the ticket is still saved.
    """
    summary:   Optional[str]            = None
    sentiment: Optional[TicketSentiment] = None
    priority:  Optional[TicketPriority]  = None
    raw_response: Optional[str]         = None   # kept for debugging / audit


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
You are an AI assistant for a customer support platform.

When given a support ticket (title + description), you must respond with a
single valid JSON object and nothing else — no markdown, no code fences,
no explanation.

The JSON must have exactly these three keys:

{
  "summary":   "<one concise sentence (max 30 words) summarising the issue>",
  "sentiment": "<one of: positive | neutral | negative>",
  "priority":  "<one of: low | medium | high | critical>"
}

Priority classification guide:
  critical — system down, data loss, security breach, complete blocking issue
  high     — major feature broken, significant business impact, no workaround
  medium   — partial functionality affected, workaround available
  low      — cosmetic issue, minor inconvenience, general question

Sentiment classification guide:
  negative — frustrated, angry, urgent, distressed language
  neutral  — factual, calm, informational tone
  positive — polite, appreciative, or constructive tone

Return ONLY the JSON object. Any deviation will cause a parsing error.
""".strip()


# ---------------------------------------------------------------------------
# Core analysis function
# ---------------------------------------------------------------------------

async def analyse_ticket(
    title: str,
    description: str,
) -> TicketAIResult:
    """
    Send the ticket to OpenAI and return structured AI analysis.

    Uses JSON mode (response_format={"type": "json_object"}) to guarantee
    the model returns parseable JSON — no brittle string parsing needed.

    Args:
        title:       Ticket title (short summary from the user).
        description: Full ticket description from the user.

    Returns:
        TicketAIResult with summary, sentiment, and priority populated.
        On any failure, returns a TicketAIResult with all fields as None
        so the caller can gracefully degrade.

    Never raises — all exceptions are caught and logged.
    """
    user_message = f"Title: {title}\n\nDescription: {description}"

    logger.info("Sending ticket to OpenAI for analysis: title=%r", title)

    try:
        response = await _client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=settings.GROQ_MAX_TOKENS,
            temperature=0.2,        # low temperature = consistent, deterministic output
            response_format={"type": "json_object"},  # JSON mode — always valid JSON
        )

        raw = response.choices[0].message.content or ""
        logger.debug("Groq raw response: %s", raw)

        return _parse_ai_response(raw)

    except RateLimitError:
        logger.error(
            "Groq rate limit exceeded. Ticket will be saved without AI fields."
        )
        return TicketAIResult()

    except APITimeoutError:
        logger.error(
            "Groq request timed out after 30s. Ticket will be saved without AI fields."
        )
        return TicketAIResult()

    except APIError as exc:
        logger.error(
            "Groq API error (status=%s): %s. Ticket will be saved without AI fields.",
            getattr(exc, "status_code", "unknown"),
            exc,
        )
        return TicketAIResult()

    except Exception as exc:
        logger.error(
            "Unexpected error during AI analysis: %s. Ticket will be saved without AI fields.",
            exc,
        )
        return TicketAIResult()


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_ai_response(raw: str) -> TicketAIResult:
    """
    Parse the raw JSON string from OpenAI into a TicketAIResult.

    Validates each field against the allowed enum values.
    Any field that is missing or invalid is set to None rather than raising.

    Args:
        raw: Raw JSON string from OpenAI response content.

    Returns:
        TicketAIResult with validated fields.
    """
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse OpenAI JSON response: %s | raw=%r", exc, raw)
        return TicketAIResult(raw_response=raw)

    # ── Summary ────────────────────────────────────────────────────────────
    summary = data.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        logger.warning("AI returned missing or empty summary. Defaulting to None.")
        summary = None
    else:
        summary = summary.strip()[:500]   # hard cap — protect VARCHAR(500) columns

    # ── Sentiment ──────────────────────────────────────────────────────────
    sentiment_raw = str(data.get("sentiment", "")).strip().lower()
    valid_sentiments = {s.value for s in TicketSentiment}
    if sentiment_raw in valid_sentiments:
        sentiment = TicketSentiment(sentiment_raw)
    else:
        logger.warning(
            "AI returned invalid sentiment %r. Valid values: %s. Defaulting to neutral.",
            sentiment_raw, valid_sentiments,
        )
        sentiment = TicketSentiment.NEUTRAL

    # ── Priority ───────────────────────────────────────────────────────────
    priority_raw = str(data.get("priority", "")).strip().lower()
    valid_priorities = {p.value for p in TicketPriority}
    if priority_raw in valid_priorities:
        priority = TicketPriority(priority_raw)
    else:
        logger.warning(
            "AI returned invalid priority %r. Valid values: %s. Defaulting to medium.",
            priority_raw, valid_priorities,
        )
        priority = TicketPriority.MEDIUM

    logger.info(
        "AI analysis complete: sentiment=%s priority=%s summary=%r",
        sentiment.value, priority.value, summary,
    )

    return TicketAIResult(
        summary=summary,
        sentiment=sentiment,
        priority=priority,
        raw_response=raw,
    )


# ---------------------------------------------------------------------------
# enrich_ticket — analyse + persist in one call
# ---------------------------------------------------------------------------

async def enrich_ticket(
    db: AsyncSession,
    ticket_id: uuid.UUID,
    owner_id: uuid.UUID,
    title: str,
    description: str,
) -> None:
    """
    Analyse a ticket with OpenAI and persist the results to the database.

    This is the main entry point called by the ticket creation route after
    the ticket is saved. It runs the full AI pipeline and writes the results
    back via ticket_service.update_ticket().

    Designed for fire-and-forget usage — all errors are caught internally
    so a failed AI call never bubbles up to the user.

    Args:
        db:          Async SQLAlchemy session.
        ticket_id:   UUID of the ticket to enrich.
        owner_id:    UUID of the ticket's owner (required by update_ticket).
        title:       Ticket title.
        description: Ticket description.

    Returns:
        None. Results are persisted directly to the database.
    """
    # Import here to avoid circular imports
    # (ticket_service imports from schemas; ai_service imports ticket_service)
    from app.services import ticket_service

    logger.info("Starting AI enrichment for ticket_id=%s", ticket_id)

    result = await analyse_ticket(title, description)

    # If all fields are None (OpenAI failed), skip the DB update entirely
    if result.summary is None and result.sentiment is None and result.priority is None:
        logger.warning(
            "AI enrichment produced no results for ticket_id=%s. Skipping DB update.",
            ticket_id,
        )
        return

    # Build a TicketUpdate with only the AI fields
    update_payload = TicketUpdate(
        ai_summary=result.summary,
        sentiment=result.sentiment,
        priority=result.priority,
    )

    try:
        await ticket_service.update_ticket(
            db=db,
            ticket_id=ticket_id,
            payload=update_payload,
            owner_id=owner_id,
        )
        logger.info(
            "AI enrichment persisted: ticket_id=%s sentiment=%s priority=%s",
            ticket_id,
            result.sentiment.value if result.sentiment else None,
            result.priority.value if result.priority else None,
        )
    except Exception as exc:
        logger.error(
            "Failed to persist AI enrichment for ticket_id=%s: %s",
            ticket_id, exc,
        )