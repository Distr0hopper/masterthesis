import uuid


class WorkflowDraftNotFoundError(Exception):
    def __init__(self, draft_id: uuid.UUID) -> None:
        super().__init__(f"Workflow draft {draft_id} not found")
        self.draft_id = draft_id


class WorkflowDraftForbiddenError(Exception):
    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message)
