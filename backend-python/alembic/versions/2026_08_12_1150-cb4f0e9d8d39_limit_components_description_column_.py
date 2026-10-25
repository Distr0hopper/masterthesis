"""limit components description column length

Revision ID: cb4f0e9d8d39
Revises: 3b45a0a8737c
Create Date: 2026-08-12 11:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cb4f0e9d8d39'
down_revision: Union[str, Sequence[str], None] = '3b45a0a8737c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'components',
        'description',
        existing_type=sa.String(),
        type_=sa.String(length=2000),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'components',
        'description',
        existing_type=sa.String(length=2000),
        type_=sa.String(),
        existing_nullable=True,
    )
