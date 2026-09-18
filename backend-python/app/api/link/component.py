from app.api.link.base import BaseLinkBuilder
from app.api.link.model import Link
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.util.endpoint import Endpoints
from app.api.util.http_method import HttpMethod
from app.application.commands.commands import ComponentCommandType
from app.domain.models.component import Component


class ComponentLinkBuilder(BaseLinkBuilder[Component, ComponentPermissionValidator]):

    def _create_validator(self) -> ComponentPermissionValidator:
        return ComponentPermissionValidator(self.current_user)

    def _get_available_links(self, entity: Component) -> dict[str, Link]:
        return {
            "self": Link(href=Endpoints.component_by_id(entity.id), method=HttpMethod.GET),
            "delete": Link(href=Endpoints.component_by_id(entity.id), method=HttpMethod.DELETE),
            "updateDescription": Link(href=Endpoints.component_commands_by_id(entity.id), method=HttpMethod.POST),
            "updateDomain": Link(href=Endpoints.component_commands_by_id(entity.id), method=HttpMethod.POST),
            "favorite": Link(href=Endpoints.component_commands_by_id(entity.id), method=HttpMethod.POST),
            "unfavorite": Link(href=Endpoints.component_commands_by_id(entity.id), method=HttpMethod.POST),
            "repackage": Link(href=Endpoints.component_commands_by_id(entity.id), method=HttpMethod.POST),
            "publish": Link(href=Endpoints.component_commands_by_id(entity.id), method=HttpMethod.POST),
        }

    def _is_link_allowed(self, rel: str, entity: Component) -> bool:
        match rel:
            case "self":
                return self._validator.can_read(entity)
            case "delete":
                return self._validator.can_delete(entity)
            case "updateDescription":
                return self._validator.can_execute(entity, ComponentCommandType.UPDATE_DESCRIPTION)
            case "updateDomain":
                return self._validator.can_execute(entity, ComponentCommandType.UPDATE_DOMAIN)
            case "favorite":
                return self._validator.can_execute(entity, ComponentCommandType.ADD_FAVORITE)
            case "unfavorite":
                return self._validator.can_execute(entity, ComponentCommandType.REMOVE_FAVORITE)
            case "repackage":
                return self._validator.can_execute(entity, ComponentCommandType.REPACKAGE)
            case "publish":
                return self._validator.can_execute(entity, ComponentCommandType.PUBLISH)
            case _:
                return False
