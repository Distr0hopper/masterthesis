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


class WorkflowStepNotMatchedError(Exception):
    def __init__(self, step_id: uuid.UUID) -> None:
        super().__init__(f"Workflow step {step_id} has no matched component to confirm")
