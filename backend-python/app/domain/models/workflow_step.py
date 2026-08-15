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


class WorkflowStep(SQLModel, table=True):
    __tablename__ = "workflow_steps"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workflow_id: uuid.UUID = Field(sa_column=Column(ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False))
    step_id: str  # the CWL step key, e.g. "step_remove_outliers"
    run_reference: str  # the raw `run:` value, e.g. "remove-outliers.cwl"
    step_order: int
    # pinned to one specific Component *version* row (not "latest of lineage") for
    # reproducibility - ondelete SET NULL (not CASCADE like Parameter) because a step
    # merely references a Component, it isn't owned by it
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
