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


class WorkflowNotReadyToPublishError(Exception):
    def __init__(self, workflow_id: uuid.UUID) -> None:
        super().__init__(f"Workflow {workflow_id} cannot be published until every step is confirmed")


class ComponentDomainRequiredError(Exception):
    def __init__(self) -> None:
        super().__init__("component_domain is required when the upload contains extracted inline components")


class InvalidExtractedComponentNameError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Extracted component name '{name}' is blank")


class DuplicateExtractedComponentNameError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"Multiple extracted components would be named '{name}' - names must be unique within one upload")


class ExtractedComponentNameCollisionError(Exception):
    def __init__(self, name: str) -> None:
        super().__init__(f"A component named '{name}' already exists - rename it before creating this workflow")


class UnsupportedInlineWorkflowStepError(Exception):
    def __init__(self, step_ids: list[str]) -> None:
        super().__init__(
            f"Step(s) {', '.join(step_ids)} have an inline run: that is not class: CommandLineTool "
            "(e.g. an inline ExpressionTool or sub-Workflow) - not supported for upload"
        )
