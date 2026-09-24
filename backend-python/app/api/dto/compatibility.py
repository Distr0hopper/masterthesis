import uuid

from pydantic import Field

from app.api.dto.base import CamelModel
from app.domain.compatibility.port_check import ConnectionStatus, UnverifiedReason

MAX_CONNECTIONS = 200


class ConnectionDto(CamelModel):
    """A builder edge: the output `sourcePort` of one component feeding the input `targetPort` of another."""

    source_component_id: uuid.UUID
    source_port: str
    target_component_id: uuid.UUID
    target_port: str


class CompatibilityRequestDto(CamelModel):
    connections: list[ConnectionDto] = Field(max_length=MAX_CONNECTIONS)


class ConnectionCheckDto(CamelModel):
    status: ConnectionStatus
    #: why the check was inconclusive - set only when status is unverified
    reason: UnverifiedReason | None
    #: ready-to-show explanation - null for a plain compatible connection
    message: str | None


class CompatibilityResponseDto(CamelModel):
    #: one per requested connection, in request order
    results: list[ConnectionCheckDto]
