from app.api.permission.base import PermissionValidator
from app.domain.models.user import User
from app.domain.models.workflow import Workflow


class WorkflowPermissionValidator(PermissionValidator[Workflow]):
    def __init__(self, user: User | None) -> None:
        super().__init__(user)

    def can_create(self) -> bool:
        return True

    def can_update(self, workflow: Workflow) -> bool:
        return workflow.created_by_id == self.user.id

    def can_delete(self, workflow: Workflow) -> bool:
        return workflow.created_by_id == self.user.id
