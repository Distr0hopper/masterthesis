from app.domain.models.user import User
from app.domain.models.workflow import Workflow


class WorkflowPermissionValidator:
    def __init__(self, user: User) -> None:
        self.user = user

    def can_create(self) -> bool:
        return True

    def can_update(self, workflow: Workflow) -> bool:
        return workflow.created_by_id == self.user.id

    def can_delete(self, workflow: Workflow) -> bool:
        return workflow.created_by_id == self.user.id
