import uuid


class WorkflowNotFoundError(Exception):
    def __init__(self, workflow_id: uuid.UUID) -> None:
        super().__init__(f"Workflow {workflow_id} not found")


class WorkflowStepNotFoundError(Exception):
    def __init__(self, step_id: uuid.UUID) -> None:
        super().__init__(f"Workflow step {step_id} not found")


class InvalidWorkflowArchiveError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid workflow archive: {reason}")


class InvalidWorkflowCwlError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(f"Invalid workflow CWL: {reason}")


class WorkflowStepNotMatchedError(Exception):
    def __init__(self, step_id: uuid.UUID) -> None:
        super().__init__(f"Workflow step {step_id} has no matched component to confirm")


class WorkflowHasUnpublishedComponentsError(Exception):
    """A workflow may only be public once every component it uses is public - otherwise
    browsing users would hit steps pointing at components they cannot see."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        super().__init__(
            f"Component(s) {', '.join(names)} are still drafts - publish them before publishing this workflow"
        )


class UnpublishableWorkflowComponentsError(Exception):
    """The workflow depends on draft components owned by someone else, so the current user
    cannot clear the blocker themselves."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        super().__init__(
            f"Component(s) {', '.join(names)} are drafts owned by another user - ask their owner to "
            "publish them before publishing this workflow"
        )


class WorkflowNotReadyToPublishError(Exception):
    def __init__(self, workflow_id: uuid.UUID) -> None:
        super().__init__(f"Workflow {workflow_id} cannot be published until every step is confirmed")


class UnconfiguredWorkflowStepError(Exception):
    def __init__(self, step_ids: list[str]) -> None:
        super().__init__(
            f"Step(s) {', '.join(step_ids)} have no component configuration - every step must either "
            "reuse an existing component or configure a new one before the workflow can be created"
        )


class InvalidComponentConfigError(Exception):
    def __init__(self, step_id: str, reason: str) -> None:
        super().__init__(f"Component configuration for step '{step_id}' is invalid: {reason}")


class InvalidExtractedComponentNameError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Extracted component name '{name}' is blank")


class DuplicateExtractedComponentNameError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Multiple extracted components would be named '{name}' - names must be unique within one upload")


class ExtractedComponentNameCollisionError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"A component named '{name}' already exists - rename it before creating this workflow")

