from app.api.link.base import BaseLinkBuilder
from app.api.link.model import Link
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.util.endpoint import Endpoints
from app.api.util.http_method import HttpMethod
from app.application.commands.commands import WorkflowStepCommandType
from app.domain.models.workflow_step import WorkflowStep


class WorkflowStepLinkBuilder(BaseLinkBuilder[WorkflowStep, ComponentPermissionValidator]):
    def _create_validator(self) -> ComponentPermissionValidator:
        return ComponentPermissionValidator(self.current_user)

    def _get_available_links(self, entity: WorkflowStep) -> dict[str, Link]:
        return {
            "update": Link(href=Endpoints.workflow_step_by_id(entity.id), method=HttpMethod.PATCH),
            "confirm": Link(href=Endpoints.workflow_step_commands_by_id(entity.id), method=HttpMethod.POST),
        }

    def _is_link_allowed(self, rel: str, entity: WorkflowStep) -> bool:
        workflow = entity.parent
        if workflow is None:
            return False
        match rel:
            case "update":
                return self._validator.can_edit_steps(workflow)
            case "confirm":
                return self._validator.can_execute_step(workflow, WorkflowStepCommandType.CONFIRM)
            case _:
                return False
