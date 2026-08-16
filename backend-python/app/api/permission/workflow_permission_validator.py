from app.api.permission.base import PermissionValidator
from app.domain.models.user import User
from app.domain.models.workflow import Workflow, WorkflowStatus


class WorkflowPermissionValidator(PermissionValidator[Workflow]):
    def __init__(self, user: User | None) -> None:
        super().__init__(user)

    def can_create(self) -> bool:
        return self.user is not None

    def can_read(self, workflow: Workflow) -> bool:
        """Mirrors WorkflowsService.get_visible_workflow: validated workflows are public, pending ones are owner-only."""
        if workflow.status == WorkflowStatus.VALIDATED:
            return True
        return self.user is not None and workflow.created_by_id == self.user.id

    def can_update(self, workflow: Workflow) -> bool:
        return self.user is not None and workflow.created_by_id == self.user.id

    def can_delete(self, workflow: Workflow) -> bool:
        return self.user is not None and workflow.created_by_id == self.user.id
