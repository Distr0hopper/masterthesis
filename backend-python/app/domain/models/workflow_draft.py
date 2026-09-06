import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, ForeignKey, Index, Text, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.user import User


class WorkflowDraft(SQLModel, table=True):
    """A workflow-builder canvas owned by one user.

    Unlike Workflow, a draft is private working state, not a published pipeline: it holds
    the React Flow canvas verbatim rather than CWL, and never appears in any public listing.
    """

    __tablename__ = "workflow_drafts"
    # every read of this table is "my drafts, newest first"; declared here rather than
    # only in the migration so autogenerate does not keep proposing to drop it
    __table_args__ = (Index("ix_workflow_drafts_created_by_id", "created_by_id", "updated_at"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    # the whole React Flow state as one JSON string - nodes (with their positions and
    # component parameters) plus edges. Kept opaque to the backend on purpose: the canvas
    # schema belongs to the frontend and may change without a migration here.
    canvas_state: str = Field(sa_column=Column(Text, nullable=False))
    # denormalised so the overview list need not parse canvas_state per row
    node_count: int = Field(default=0)
    # NOT NULL with ON DELETE CASCADE: a draft is private working state with no meaning
    # once its owner is gone (unlike Workflow.created_by_id, which is nullable so a
    # published workflow survives its author)
    created_by_id: uuid.UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False))
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    # lazy="selectin": see the matching note on Component - required for AsyncSession safety.
    # No back_populates - User deliberately exposes no `drafts` collection, so loading a
    # user never drags their whole canvas history along.
    created_by: Optional["User"] = Relationship(sa_relationship_kwargs={"lazy": "selectin"})
