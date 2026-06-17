"""add screenshot_url to tickets

Revision ID: b2f1c9a4d7e8
Revises: 039d73556912
Create Date: 2026-06-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2f1c9a4d7e8'
down_revision: Union[str, Sequence[str], None] = '039d73556912'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'tickets',
        sa.Column(
            'screenshot_url',
            sa.String(length=500),
            nullable=True,
            comment='URL of an optional screenshot attached to the ticket.',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('tickets', 'screenshot_url')
