"""add status and deprecation_note columns to components

Revision ID: a3f71c2b9d54
Revises: 5b88e4260cae
Create Date: 2026-09-18 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'a3f71c2b9d54'
down_revision: Union[str, Sequence[str], None] = '5b88e4260cae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default='published' backfills every pre-existing row as published - components
    # were unconditionally public before this column existed, so nothing may silently
    # disappear from the catalogue on upgrade.
    op.add_column(
        'components',
        sa.Column(
            'status',
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default='published',
        ),
    )
    # ...but from here on a new row is a draft until explicitly published. The app always
    # supplies the value itself (Component.status defaults to DRAFT); this only covers
    # inserts that bypass the model.
    op.alter_column('components', 'status', server_default='draft')
    # why a version is deprecated (status 'deprecated'), npm-style - NULL in every other status
    op.add_column('components', sa.Column('deprecation_note', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('components', 'deprecation_note')
    op.drop_column('components', 'status')
