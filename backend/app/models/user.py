"""
models/user.py — SQLAlchemy ORM model for the User entity.
Updated to include the tickets relationship back_populates.
"""

import uuid
from sqlalchemy import Boolean, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
        nullable=False,
    )

    username: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        server_default=text("'user'"),
        nullable=False,
    )

    # ── Relationship ───────────────────────────────────────────────────────
    # back_populates="owner" matches the `owner` attribute on the Ticket model.
    # cascade="all, delete-orphan" — deleting a user also deletes their tickets.
    # lazy="select" is fine here since we rarely need tickets when loading a user.

    tickets: Mapped[list["Ticket"]] = relationship(   # type: ignore[name-defined]
        "Ticket",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} username={self.username!r} "
            f"email={self.email!r} active={self.is_active}>"
        )

    def __str__(self) -> str:
        return self.username