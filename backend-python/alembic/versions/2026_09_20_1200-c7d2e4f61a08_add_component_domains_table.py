"""add component_domains table

Revision ID: c7d2e4f61a08
Revises: a3f71c2b9d54
Create Date: 2026-09-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'c7d2e4f61a08'
down_revision: Union[str, Sequence[str], None] = 'a3f71c2b9d54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    A component used to carry exactly one `domain`; it now spans several, matching how a
    workflow already worked. The existing value is copied into the new table *before* the
    column is dropped, so every component keeps the domain it was created with.
    """
    op.create_table(
        'component_domains',
        sa.Column('component_id', sa.Uuid(), nullable=False),
        sa.Column('domain', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(['component_id'], ['components.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('component_id', 'domain'),
    )
    op.execute(
        """
        INSERT INTO component_domains (component_id, domain)
        SELECT id, domain FROM components WHERE domain IS NOT NULL
        """
    )
    op.drop_column('components', 'domain')


def downgrade() -> None:
    """Downgrade schema.

    Lossy by nature: a component may now hold several domains and the column can only
    take one, so the alphabetically-first is kept and the rest are dropped.
    """
    op.add_column('components', sa.Column('domain', sa.VARCHAR(), nullable=True))
    op.execute(
        """
        UPDATE components c
        SET domain = (
            SELECT cd.domain FROM component_domains cd
            WHERE cd.component_id = c.id
            ORDER BY cd.domain
            LIMIT 1
        )
        """
    )
    op.execute("DELETE FROM components WHERE domain IS NULL")
    op.alter_column('components', 'domain', nullable=False)
    op.drop_table('component_domains')
