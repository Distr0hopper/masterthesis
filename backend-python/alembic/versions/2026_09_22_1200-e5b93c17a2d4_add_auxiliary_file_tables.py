"""add workflow_files and component_files tables

Revision ID: e5b93c17a2d4
Revises: d4a81f2c93be
Create Date: 2026-09-22 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'e5b93c17a2d4'
down_revision: Union[str, Sequence[str], None] = 'd4a81f2c93be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Auxiliary files a CWL document pulls in via $import/$include - SchemaDefRequirement
    type definitions in practice. They used to be dropped on upload, which left every
    download missing a file the CWL referenced.

    Keyed by path rather than basename: the $import writes a path and that exact path has
    to resolve in the archive we hand back. No backfill - nothing stored so far has them.
    """
    for table, parent, fk_column in (
        ("workflow_files", "workflows", "workflow_id"),
        ("component_files", "components", "component_id"),
    ):
        op.create_table(
            table,
            sa.Column(fk_column, sa.Uuid(), nullable=False),
            sa.Column('path', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('content', sa.Text(), nullable=False),
            sa.ForeignKeyConstraint([fk_column], [f'{parent}.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint(fk_column, 'path'),
        )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('component_files')
    op.drop_table('workflow_files')
