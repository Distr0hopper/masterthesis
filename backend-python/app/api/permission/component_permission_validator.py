from app.api.permission.base import PermissionValidator
from app.application.commands.commands import ComponentCommandType, ToolCommandType, WorkflowStepCommandType
from app.application.commands.registry import is_owner
from app.application.service.components_service import COMPONENT_COMMANDS
from app.application.service.tools_service import TOOL_COMMANDS
from app.domain.composite import lifecycle
from app.domain.models.component import Component
from app.domain.models.user import User


class ComponentPermissionValidator(PermissionValidator[Component]):
    """One set of rules for both kinds of the composite, plus the few only one kind has."""

    def __init__(self, user: User | None) -> None:
        super().__init__(user)

    def can_create(self) -> bool:
        return self.user is not None

    def can_read(self, component: Component) -> bool:
        """Mirrors ComponentsService.is_visible: public components (published or deprecated)
        are readable by everyone, drafts by their owner only."""
        if lifecycle.is_public(component):
            return True
        return self.user is not None and component.created_by_id == self.user.id

    def can_update(self, component: Component) -> bool:
        return is_owner(self.user, component)

    def can_delete(self, component: Component) -> bool:
        return is_owner(self.user, component)

    def can_execute(self, component: Component, action: str | ComponentCommandType) -> bool:
        """Whether COMPONENT_COMMANDS lets this user run `action` - each command declares it."""
        try:
            command = ComponentCommandType.from_string(str(action))
        except (ValueError, TypeError):
            return False
        return COMPONENT_COMMANDS[command].allowed(self.user, component)

    def can_execute_tool(self, component: Component, action: str | ToolCommandType) -> bool:
        """Whether TOOL_COMMANDS lets this user run `action` - each command declares it."""
        try:
            command = ToolCommandType.from_string(str(action))
        except (ValueError, TypeError):
            return False
        return TOOL_COMMANDS[command].allowed(self.user, component)

    def can_edit_steps(self, workflow: Component) -> bool:
        """A workflow's steps are its creator's to rebind - while it is a draft. A published
        workflow is what others see and nest, so it is unpublished first."""
        return workflow.is_workflow and self.can_update(workflow) and lifecycle.steps_editable(workflow)

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
