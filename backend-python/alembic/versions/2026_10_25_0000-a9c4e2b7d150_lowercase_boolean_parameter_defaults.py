"""lowercase boolean parameter defaults

Data-only repair: the CWL parser stored a non-string default with str(), so a boolean
`default: true` became Python's `True`. The builder and the tool's inputs.yaml read
booleans as `true`/`false`, so the default showed (and exported) as false. The parser now
stores such defaults as JSON.

Revision ID: a9c4e2b7d150
Revises: b8e2d4f7a913
Create Date: 2026-10-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a9c4e2b7d150'
down_revision: Union[str, Sequence[str], None] = 'b8e2d4f7a913'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE parameters
        SET default_value = lower(default_value)
        WHERE lower(cwl_type) = 'boolean' AND default_value IN ('True', 'False')
        """
    )


def downgrade() -> None:
    # `True` was never a valid value to read back - restoring it would only reintroduce the bug
    pass
