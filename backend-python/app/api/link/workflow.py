from app.api.link.base import BaseLinkBuilder
from app.api.link.model import Link
from app.api.permission.workflow_permission_validator import WorkflowPermissionValidator
from app.api.util.endpoint import Endpoints
from app.api.util.http_method import HttpMethod
from app.application.commands.commands import WorkflowCommandType
from app.domain.models.workflow import Workflow


class WorkflowLinkBuilder(BaseLinkBuilder[Workflow, WorkflowPermissionValidator]):
    def _create_validator(self) -> WorkflowPermissionValidator:
        return WorkflowPermissionValidator(self.current_user)

    def _get_available_links(self, entity: Workflow) -> dict[str, Link]:
        return {
            "self": Link(href=Endpoints.workflow_by_id(entity.id), method=HttpMethod.GET),
            "delete": Link(href=Endpoints.workflow_by_id(entity.id), method=HttpMethod.DELETE),
            "publish": Link(href=Endpoints.workflow_commands_by_id(entity.id), method=HttpMethod.POST),
        }

    def _is_link_allowed(self, rel: str, entity: Workflow) -> bool:
        match rel:
            case "self":
                return self._validator.can_read(entity)
            case "delete":
                return self._validator.can_delete(entity)
            case "publish":
                return self._validator.can_execute(entity, WorkflowCommandType.PUBLISH)
            case _:
                return False
