from app.api.permission.base import PermissionValidator
from app.application.commands.commands import ComponentCommandType, ToolCommandType, WorkflowStepCommandType
from app.domain.models.component import Component, ComponentStatus
from app.domain.models.user import User


class ComponentPermissionValidator(PermissionValidator[Component]):
    """One set of rules for both kinds of the composite, plus the few only one kind has."""

    def __init__(self, user: User | None) -> None:
        super().__init__(user)

    def can_create(self) -> bool:
        return self.user is not None

    def can_read(self, component: Component) -> bool:
        """Mirrors ComponentsService.is_visible: published components are public, drafts are owner-only."""
        if component.status == ComponentStatus.PUBLISHED:
            return True
        return self.user is not None and component.created_by_id == self.user.id

    def can_update(self, component: Component) -> bool:
        return self.user is not None and component.created_by_id == self.user.id

    def can_delete(self, component: Component) -> bool:
        return self.user is not None and component.created_by_id == self.user.id

    def can_favorite(self) -> bool:
        return self.user is not None

    def can_execute(self, component: Component, action: str | ComponentCommandType) -> bool:
        try:
            command = ComponentCommandType.from_string(str(action))
        except (ValueError, TypeError):
            return False

        match command:
            case ComponentCommandType.ADD_FAVORITE | ComponentCommandType.REMOVE_FAVORITE:
                return self.can_favorite()
            case (
                ComponentCommandType.PUBLISH
                | ComponentCommandType.UNPUBLISH
                | ComponentCommandType.UPDATE_DESCRIPTION
                | ComponentCommandType.UPDATE_DOMAIN
            ):
                return self.can_update(component)
            case _:
                return False

    def can_execute_tool(self, component: Component, action: str | ToolCommandType) -> bool:
        if not component.is_tool:
            return False
        try:
            command = ToolCommandType.from_string(str(action))
        except (ValueError, TypeError):
            return False

        match command:
            case ToolCommandType.REPACKAGE | ToolCommandType.UPDATE_FORMAT_LABELS:
                return self.can_update(component)
            case _:
                return False

    def can_edit_steps(self, workflow: Component) -> bool:
        """A workflow's steps are its creator's to rebind - while it is a draft. A published
        workflow is what others see and nest, so it is unpublished first."""
        return workflow.is_workflow and self.can_update(workflow) and workflow.status == ComponentStatus.DRAFT

    def can_execute_step(self, workflow: Component, action: str | WorkflowStepCommandType) -> bool:
        try:
            command = WorkflowStepCommandType.from_string(str(action))
        except (ValueError, TypeError):
            return False

        match command:
            case WorkflowStepCommandType.CONFIRM:
                return self.can_edit_steps(workflow)
            case _:
                return False
