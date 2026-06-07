"""
db/base.py — SQLAlchemy declarative base + shared mixins.

Import ALL models at the bottom so Alembic and create_all()
can see the full metadata graph from a single import.
"""

import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base. Subclass this in every ORM model."""
    pass


class TimestampMixin:
    """
    Adds created_at and updated_at audit columns to any model.

    Usage:
        class Ticket(TimestampMixin, Base):
            __tablename__ = "tickets"
    """
    created_at: MappedColumn[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: MappedColumn[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Model imports — must stay at the bottom to avoid circular imports.
# Every model listed here becomes visible to Alembic and create_all().
# ---------------------------------------------------------------------------

from app.models.user import User      # noqa: F401, E402
from app.models.ticket import Ticket  # noqa: F401, E402