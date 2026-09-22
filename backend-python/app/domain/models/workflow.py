import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.user import User
    from app.domain.models.workflow_domain import WorkflowDomain
    from app.domain.models.workflow_file import WorkflowFile
    from app.domain.models.workflow_step import WorkflowStep


MAX_DESCRIPTION_LENGTH = 2000


class WorkflowStatus(str, Enum):
    PENDING_VALIDATION = "pending_validation"
    VALIDATED = "validated"


class WorkflowSource(str, Enum):
    """How the workflow got here - mirrors ComponentSource."""

    WORKFLOW_BUILDER = "workflow_builder"
    MANUAL_UPLOAD = "manual_upload"


class Workflow(SQLModel, table=True):
    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("name", name="uq_workflows_name"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    description: str | None = Field(default=None, sa_column=Column(String(MAX_DESCRIPTION_LENGTH), nullable=True))
    created_by_id: uuid.UUID | None = Field(default=None, sa_column=Column(ForeignKey("users.id"), nullable=True))
    # the raw pipeline CWL content (class: Workflow), stored verbatim for download/rebuild
    cwl_content: str = Field(sa_column=Column(Text, nullable=False))
    # explicit String column, same convention as StepMatchStatus/Component.source - never a
    # native PG enum. Only VALIDATED workflows are publicly visible/listed (see
    # WorkflowsRepository.find_all / WorkflowsService.get_visible_workflow) - a workflow
    # flips to VALIDATED only once every one of its steps is explicitly CONFIRMED.
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING_VALIDATION, sa_column=Column(String, nullable=False))
    # explicit String column, same convention as status/Component.source - never a native
    # PG enum. Everything that predates the builder was uploaded as an archive, hence the
    # MANUAL_UPLOAD default (and the matching server_default in the migration).
    source: WorkflowSource = Field(default=WorkflowSource.MANUAL_UPLOAD, sa_column=Column(String, nullable=False))
    # the builder draft this was published from, so the UI can offer "edit in builder".
    # ON DELETE SET NULL, not CASCADE: deleting the draft must not delete the published
    # workflow - it just stops being editable in the builder.
    # index: WorkflowsRepository.find_by_draft_id / find_all_by_draft_ids look up by it.
    draft_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("workflow_drafts.id", ondelete="SET NULL"), nullable=True, index=True
        ),
    )
    created_at: datetime = Field(sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False))
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    )

    # lazy="selectin": see the matching note on Component - required for AsyncSession safety
    created_by: Optional["User"] = Relationship(back_populates="workflows", sa_relationship_kwargs={"lazy": "selectin"})
    # cascade="all, delete-orphan" + passive_deletes=True: both children's FKs are NOT
    # NULL with DB-level ON DELETE CASCADE (workflow_domains.workflow_id is even part of
    # its composite PK) - without delete-orphan, SQLAlchemy's default "nullify" cascade
    # tries to blank out those FK columns itself before the parent DELETE, which SQLAlchemy
    # refuses outright for a PK column and would violate NOT NULL otherwise; passive_deletes
    # then tells it to trust the DB's cascade instead of issuing per-child DELETEs itself
    steps: list["WorkflowStep"] = Relationship(
        back_populates="workflow",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "order_by": "WorkflowStep.step_order",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
    domains: list["WorkflowDomain"] = Relationship(
        back_populates="workflow",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True},
    )
    files: list["WorkflowFile"] = Relationship(
        back_populates="workflow",
        sa_relationship_kwargs={"lazy": "selectin", "cascade": "all, delete-orphan", "passive_deletes": True},
    )
