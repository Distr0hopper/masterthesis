from app.api.permission.base import PermissionValidator
from app.domain.models.user import User
from app.domain.models.workflow_draft import WorkflowDraft


class WorkflowDraftPermissionValidator(PermissionValidator[WorkflowDraft]):
    """A builder canvas is private working state: only its creator sees or changes it -
    unlike a Component, there is no public status that opens it up to others."""

    def __init__(self, user: User | None) -> None:
        super().__init__(user)

    def can_create(self) -> bool:
        return self.user is not None

    def can_read(self, draft: WorkflowDraft) -> bool:
        return self._is_owner(draft)

    def can_update(self, draft: WorkflowDraft) -> bool:
        return self._is_owner(draft)

    def can_delete(self, draft: WorkflowDraft) -> bool:
        return self._is_owner(draft)

    def _is_owner(self, draft: WorkflowDraft) -> bool:
        return self.user is not None and draft.created_by_id == self.user.id
