"""add components and parameters tables

Revision ID: b1c9a6e2f4d7
Revises: eaaa05e8f17a
Create Date: 2026-08-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'b1c9a6e2f4d7'
down_revision: Union[str, Sequence[str], None] = 'eaaa05e8f17a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'components',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('author_name', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_by_id', sa.Uuid(), nullable=True),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('repo_url', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('repo_commit_sha', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('doi', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
        sa.Column('cwl_content', sa.Text(), nullable=False),
        sa.Column('source', sqlmodel.sql.sqltypes.AutoString(), server_default=sa.text("'manual_upload'"), nullable=False),
        sa.Column('domain', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_components_name_version'),
    )
    op.create_index(
        'uq_components_name_repo_commit_sha',
        'components',
        ['name', 'repo_commit_sha'],
        unique=True,
        postgresql_where=sa.text('repo_commit_sha IS NOT NULL'),
    )

    op.create_table(
        'parameters',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('cwl_type', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('default_value', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('direction', sqlmodel.sql.sqltypes.AutoString(), server_default=sa.text("'input'"), nullable=False),
        sa.Column('component_id', sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(['component_id'], ['components.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('parameters')
    op.drop_index('uq_components_name_repo_commit_sha', table_name='components')
    op.drop_table('components')