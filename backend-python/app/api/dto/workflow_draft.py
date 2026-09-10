import uuid
from datetime import datetime

from pydantic import Field

from app.api.dto.base import CamelModel

MAX_NAME_LENGTH = 200
# generous but bounded - a canvas is a few KB in practice; the cap stops a runaway
# client from writing an unbounded blob into the TEXT column
MAX_CANVAS_STATE_LENGTH = 1_000_000


class WorkflowDraftListItemDto(CamelModel):
    id: uuid.UUID
    name: str
    node_count: int
    updated_at: datetime


class WorkflowDraftDetailDto(CamelModel):
    id: uuid.UUID
    name: str
    # raw JSON string, opaque to the backend - the frontend parses it back into
    # React Flow nodes/edges
    canvas_state: str
    node_count: int
    updated_at: datetime
    created_at: datetime


class WorkflowDraftWriteRequestDto(CamelModel):
    """Body for both create and update - the editor always sends the full canvas."""

    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    canvas_state: str = Field(max_length=MAX_CANVAS_STATE_LENGTH)
    node_count: int = Field(ge=0)


class SyncedWorkflowDto(CamelModel):

    workflow_id: uuid.UUID
    name: str
    step_count: int
