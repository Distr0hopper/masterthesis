from dataclasses import dataclass
from enum import StrEnum


class ComponentCommandType(StrEnum):
    ADD_FAVORITE = "ADD_FAVORITE"
    REMOVE_FAVORITE = "REMOVE_FAVORITE"
    REPACKAGE = "REPACKAGE"
    PUBLISH = "PUBLISH"
    UNPUBLISH = "UNPUBLISH"
    UPDATE_DESCRIPTION = "UPDATE_DESCRIPTION"
    UPDATE_DOMAIN = "UPDATE_DOMAIN"

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


@dataclass
class ComponentCommand:
    type: ComponentCommandType
    note: str | None = None
    description: str | None = None
    domains: list[str] | None = None


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
