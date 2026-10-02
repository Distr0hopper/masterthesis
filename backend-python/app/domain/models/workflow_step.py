import uuid
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, ForeignKey, String
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.component import Component
    from app.domain.models.workflow import Workflow


class StepMatchStatus(str, Enum):
    SUGGESTED = "suggested"
    CONFIRMED = "confirmed"
    UNMATCHED = "unmatched"
    INLINE = "inline"


#: step states that need no further action before a workflow can be published - either the
#: user confirmed the component, or the step runs inline and never had one to confirm
SETTLED_STEP_STATUSES = {StepMatchStatus.CONFIRMED, StepMatchStatus.INLINE}


class WorkflowStep(SQLModel, table=True):
    """One step of a workflow - the edge of the composite, from a Workflow to the child
    Component it runs."""

    __tablename__ = "workflow_steps"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # the parent - references the workflow detail row, so a step can only ever belong to a
    # component of kind WORKFLOW
    workflow_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("workflows.component_id", ondelete="CASCADE"), nullable=False)
    )
    step_id: str  # the CWL step key, e.g. "step_remove_outliers"
    run_reference: str  # the raw `run:` value, e.g. "remove-outliers.cwl"
    step_order: int
    # the child - any Component, a Tool or (nested) another Workflow. Pinned to one specific
    # *version* row (not "latest of lineage") for reproducibility - ondelete SET NULL (not
    # CASCADE like Parameter) because a step merely references a Component, it isn't owned by it
    component_id: uuid.UUID | None = Field(
        default=None, sa_column=Column(ForeignKey("components.id", ondelete="SET NULL"), nullable=True)
    )
    # explicit String column: SQLModel would otherwise infer a native Postgres enum type
    # from the Python Enum, which we deliberately avoided (see Component.source / Parameter.direction)
    match_status: StepMatchStatus = Field(
        default=StepMatchStatus.UNMATCHED, sa_column=Column(String, nullable=False)
    )
    # fuzzy-match confidence at suggestion time; retained for display even after confirmation
    match_score: float | None = None

    workflow: Optional["Workflow"] = Relationship(back_populates="steps", sa_relationship_kwargs={"lazy": "selectin"})
    component: Optional["Component"] = Relationship(sa_relationship_kwargs={"lazy": "selectin"})

    @property
    def parent(self) -> Optional["Component"]:
        """The workflow Component this step belongs to."""
        return self.workflow.component if self.workflow is not None else None
