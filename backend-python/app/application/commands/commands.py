from dataclasses import dataclass
from enum import StrEnum

from app.domain.models.parameter import ParameterDirection


class ComponentCommandType(StrEnum):
    ADD_FAVORITE = "ADD_FAVORITE"
    REMOVE_FAVORITE = "REMOVE_FAVORITE"
    REPACKAGE = "REPACKAGE"
    PUBLISH = "PUBLISH"
    UNPUBLISH = "UNPUBLISH"
    UPDATE_DESCRIPTION = "UPDATE_DESCRIPTION"
    UPDATE_DOMAIN = "UPDATE_DOMAIN"
    UPDATE_FORMAT_LABELS = "UPDATE_FORMAT_LABELS"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "ComponentCommandType":
        if not isinstance(value, str):
            raise TypeError(f"command must be str or ComponentCommandType, got {type(value).__name__}")
        try:
            return cls(value.strip().upper())
        except ValueError as e:
            allowed = ", ".join(c.value for c in cls)
            raise ValueError(f"Unknown command '{value}'. Allowed: {allowed}") from e


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
    description: str | None = None
    domains: list[str] | None = None
    #: payload for UPDATE_FORMAT_LABELS
    format_labels: list[ManualFormatLabel] | None = None


class WorkflowCommandType(StrEnum):
    ADD_FAVORITE = "ADD_FAVORITE"
    REMOVE_FAVORITE = "REMOVE_FAVORITE"
    PUBLISH = "PUBLISH"
    UNPUBLISH = "UNPUBLISH"
    UPDATE_DESCRIPTION = "UPDATE_DESCRIPTION"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "WorkflowCommandType":
        if not isinstance(value, str):
            raise TypeError(f"command must be str or WorkflowCommandType, got {type(value).__name__}")
        try:
            return cls(value.strip().upper())
        except ValueError as e:
            allowed = ", ".join(c.value for c in cls)
            raise ValueError(f"Unknown command '{value}'. Allowed: {allowed}") from e


@dataclass
class WorkflowCommand:
    type: WorkflowCommandType
    note: str | None = None
    # payload for UPDATE_DESCRIPTION - the new description (None clears it); ignored by other commands
    description: str | None = None
    #: PUBLISH only - also publish the workflow's still-draft components
    publish_components: bool = False


class WorkflowStepCommandType(StrEnum):
    CONFIRM = "CONFIRM"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> "WorkflowStepCommandType":
        if not isinstance(value, str):
            raise TypeError(f"command must be str or WorkflowStepCommandType, got {type(value).__name__}")
        try:
            return cls(value.strip().upper())
        except ValueError as e:
            allowed = ", ".join(c.value for c in cls)
            raise ValueError(f"Unknown command '{value}'. Allowed: {allowed}") from e


@dataclass
class WorkflowStepCommand:
    type: WorkflowStepCommandType
    note: str | None = None
