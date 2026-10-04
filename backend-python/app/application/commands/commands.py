from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from app.domain.models.parameter import ParameterDirection


class CommandType(StrEnum):
    """Base of every command enum - memberless, so the concrete enums below may extend it."""

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> Self:
        if not isinstance(value, str):
            raise TypeError(f"command must be str or {cls.__name__}, got {type(value).__name__}")
        try:
            return cls(value.strip().upper())
        except ValueError as e:
            allowed = ", ".join(c.value for c in cls)
            raise ValueError(f"Unknown command '{value}'. Allowed: {allowed}") from e


class ComponentCommandType(CommandType):
    """Commands every component understands, whatever its kind."""

    ADD_FAVORITE = "ADD_FAVORITE"
    REMOVE_FAVORITE = "REMOVE_FAVORITE"
    PUBLISH = "PUBLISH"
    UNPUBLISH = "UNPUBLISH"
    UPDATE_DESCRIPTION = "UPDATE_DESCRIPTION"
    UPDATE_DOMAIN = "UPDATE_DOMAIN"


class ToolCommandType(CommandType):
    """Commands only a tool - the leaf of the composite - understands."""

    REPACKAGE = "REPACKAGE"
    UPDATE_FORMAT_LABELS = "UPDATE_FORMAT_LABELS"


class WorkflowStepCommandType(CommandType):
    CONFIRM = "CONFIRM"


@dataclass(frozen=True)
class ManualFormatLabel:
    """A hand-written format label for a File port whose format no ontology covers (e.g.
    "RDS"). Addressed by name + direction, since a port has no id before it is persisted.
    Display only - it never makes a connection count as verified."""

    name: str
    direction: ParameterDirection
    #: None (or blank) clears the label
    label: str | None


@dataclass
class ComponentCommand:
    type: ComponentCommandType
    note: str | None = None
    #: payload for UPDATE_DESCRIPTION - the new description (None clears it)
    description: str | None = None
    #: payload for UPDATE_DOMAIN
    domains: list[str] | None = None
    #: PUBLISH of a workflow only - also publish its still-draft children
    publish_components: bool = False
    #: UNPUBLISH only - also unpublish the caller's own public workflows that run this
    #: version, at any depth (other users' ones always block)
    unpublish_parents: bool = False


@dataclass
class ToolCommand:
    type: ToolCommandType
    note: str | None = None
    #: payload for UPDATE_FORMAT_LABELS
    format_labels: list[ManualFormatLabel] | None = None


@dataclass
class WorkflowStepCommand:
    type: WorkflowStepCommandType
    note: str | None = None
