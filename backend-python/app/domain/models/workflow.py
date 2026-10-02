import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.domain.models.component import Component
    from app.domain.models.workflow_step import WorkflowStep


class Workflow(SQLModel, table=True):
    """The composite: what only a workflow has - its steps, each running another Component
    (a Tool, or another Workflow).

    Everything shared with tools (name, version, CWL, ports, ...) is on the owning
    Component; this row only exists alongside one of kind WORKFLOW.
    """

    __tablename__ = "workflows"

    component_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("components.id", ondelete="CASCADE"), primary_key=True)
    )
    # the builder draft this was published from, so the UI can offer "edit in builder".
    # Every version synced from one draft carries it. ON DELETE SET NULL, not CASCADE:
    # deleting the draft must not delete the published workflow - it just stops being
    # editable in the builder.
    # index: WorkflowsRepository.find_latest_by_draft_id / find_all_by_draft_ids look up by it.
    draft_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("workflow_drafts.id", ondelete="SET NULL"), nullable=True, index=True),
    )

    component: "Component" = Relationship(back_populates="workflow", sa_relationship_kwargs={"lazy": "selectin"})
    # cascade="all, delete-orphan" + passive_deletes=True: the steps' FK is NOT NULL with
    # DB-level ON DELETE CASCADE - without delete-orphan, SQLAlchemy's default "nullify"
    # cascade tries to blank out the FK column itself before the parent DELETE, which
    # violates NOT NULL; passive_deletes then tells it to trust the DB's cascade instead of
    # issuing per-step DELETEs itself
    steps: list["WorkflowStep"] = Relationship(
        back_populates="workflow",
        sa_relationship_kwargs={
            "lazy": "selectin",
            "order_by": "WorkflowStep.step_order",
            "cascade": "all, delete-orphan",
            "passive_deletes": True,
        },
    )
