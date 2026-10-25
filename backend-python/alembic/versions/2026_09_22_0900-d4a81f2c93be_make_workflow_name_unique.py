"""make workflow name unique

Revision ID: d4a81f2c93be
Revises: c7d2e4f61a08
Create Date: 2026-09-22 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4a81f2c93be'
down_revision: Union[str, Sequence[str], None] = 'c7d2e4f61a08'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

#: rename duplicates rather than fail the migration - existing workflows predate the rule
#: and dropping or refusing them would be worse than a suffixed name. The oldest row of
#: each name keeps it; the rest become "<name> (2)", "<name> (3)", ...
_DEDUPE = """
    WITH ranked AS (
        SELECT id, name, row_number() OVER (PARTITION BY name ORDER BY created_at, id) AS rn
        FROM workflows
    )
    UPDATE workflows w
    SET name = r.name || ' (' || r.rn || ')'
    FROM ranked r
    WHERE w.id = r.id AND r.rn > 1
"""


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()
    # repeated because a generated "<name> (2)" can itself collide with a workflow already
    # called that - each pass only touches rows that are still duplicated, so this settles
    # quickly; the cap only guards against a pathological dataset looping forever.
    for _ in range(10):
        if conn.execute(sa.text(_DEDUPE)).rowcount == 0:
            break

    op.create_unique_constraint("uq_workflows_name", "workflows", ["name"])


def downgrade() -> None:
    """Downgrade schema.

    Only the constraint is dropped - the names rewritten on the way up are not restored,
    since the originals are not recorded anywhere.
    """
    op.drop_constraint("uq_workflows_name", "workflows", type_="unique")
