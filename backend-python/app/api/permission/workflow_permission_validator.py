from app.api.permission.base import PermissionValidator
from app.application.commands.commands import WorkflowCommandType, WorkflowStepCommandType
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

    def can_execute(self, workflow: Workflow, action: str | WorkflowCommandType) -> bool:
        try:
            command = WorkflowCommandType.from_string(str(action))
        except (ValueError, TypeError):
            return False

        match command:
            case WorkflowCommandType.PUBLISH:
                return self.can_update(workflow)
            case WorkflowCommandType.UPDATE_DESCRIPTION:
                return self.can_update(workflow)
            case _:
                return False

    def can_execute_step(self, workflow: Workflow, action: str | WorkflowStepCommandType) -> bool:
        try:
            command = WorkflowStepCommandType.from_string(str(action))
        except (ValueError, TypeError):
            return False

        match command:
            case WorkflowStepCommandType.CONFIRM:
                return self.can_update(workflow)
            case _:
                return False
