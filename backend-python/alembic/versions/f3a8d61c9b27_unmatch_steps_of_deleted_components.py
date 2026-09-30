"""unmatch steps whose component was deleted

Data-only repair: before component deletion cascaded into workflow steps, the FK's
ON DELETE SET NULL left such steps CONFIRMED/SUGGESTED with no component, and their
workflow VALIDATED (public) despite being broken. INLINE steps never have a component
and are left alone.

Revision ID: f3a8d61c9b27
Revises: e5b93c17a2d4
Create Date: 2026-09-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f3a8d61c9b27'
down_revision: Union[str, Sequence[str], None] = 'e5b93c17a2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE workflow_steps
        SET match_status = 'unmatched', match_score = NULL
        WHERE component_id IS NULL AND match_status IN ('confirmed', 'suggested')
        """
    )
    op.execute(
        """
        UPDATE workflows
        SET status = 'pending_validation'
        WHERE status = 'validated'
          AND EXISTS (
              SELECT 1 FROM workflow_steps s
              WHERE s.workflow_id = workflows.id AND s.match_status = 'unmatched'
          )
        """
    )


def downgrade() -> None:
    # the original statuses are not recoverable, and restoring them would only
    # reintroduce the inconsistency this revision repairs
    pass
