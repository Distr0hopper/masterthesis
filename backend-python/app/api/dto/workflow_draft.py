import uuid
from datetime import datetime

from pydantic import Field

from app.api.dto.base import CamelModel
from app.domain.models.component import ComponentStatus

MAX_NAME_LENGTH = 200
# generous but bounded - a canvas is a few KB in practice; the cap stops a runaway
# client from writing an unbounded blob into the TEXT column
MAX_CANVAS_STATE_LENGTH = 1_000_000


class LinkedWorkflowDto(CamelModel):
    """The newest version a draft's Save synced into My Components - what the next Save
    overwrites while it is a draft, and builds the next version on once it isn't."""

    id: uuid.UUID
    version: int
    status: ComponentStatus


class WorkflowDraftListItemDto(CamelModel):
    id: uuid.UUID
    name: str
    node_count: int
    updated_at: datetime
    # the Workflow this draft has been synced to in My Workflows, if any - drives the
    # "also delete the My Workflows copy?" prompt on delete
    linked_workflow: LinkedWorkflowDto | None = None


class WorkflowDraftDetailDto(CamelModel):
    id: uuid.UUID
    name: str
    # raw JSON string, opaque to the backend - the frontend parses it back into
    # React Flow nodes/edges
    canvas_state: str
    node_count: int
    updated_at: datetime
    created_at: datetime
    linked_workflow: LinkedWorkflowDto | None = None
    # componentIds on the canvas whose component has since been deleted - the builder
    # flags those nodes on open instead of failing later on connect/save/export
    missing_component_ids: list[str] = []


class WorkflowDraftWriteRequestDto(CamelModel):
    """Body for both create and update - the editor always sends the full canvas."""

    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    canvas_state: str = Field(max_length=MAX_CANVAS_STATE_LENGTH)
    node_count: int = Field(ge=0)


class SyncedWorkflowDto(CamelModel):

    workflow_id: uuid.UUID
    name: str
    step_count: int
    version: int
    status: ComponentStatus
