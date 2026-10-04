from app.api.link.base import BaseLinkBuilder
from app.api.link.model import Link
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.util.endpoint import Endpoints
from app.api.util.http_method import HttpMethod
from app.application.commands.commands import ComponentCommandType, ToolCommandType
from app.domain.models.component import Component


class ComponentLinkBuilder(BaseLinkBuilder[Component, ComponentPermissionValidator]):
    """The links of either kind - the shared ones on /components, plus the tool-only
    ones on /tools for a tool."""

    def _create_validator(self) -> ComponentPermissionValidator:
        return ComponentPermissionValidator(self.current_user)

    def _get_available_links(self, entity: Component) -> dict[str, Link]:
        commands = Endpoints.component_commands_by_id(entity.id)
        links = {
            "self": Link(href=Endpoints.component_by_id(entity.id), method=HttpMethod.GET),
            "download": Link(href=Endpoints.component_download_by_id(entity.id), method=HttpMethod.GET),
            "delete": Link(href=Endpoints.component_by_id(entity.id), method=HttpMethod.DELETE),
            "impact": Link(href=Endpoints.component_impact_by_id(entity.id), method=HttpMethod.GET),
            "updateDescription": Link(href=commands, method=HttpMethod.POST),
            "updateDomain": Link(href=commands, method=HttpMethod.POST),
            "favorite": Link(href=commands, method=HttpMethod.POST),
            "unfavorite": Link(href=commands, method=HttpMethod.POST),
            "publish": Link(href=commands, method=HttpMethod.POST),
            "unpublish": Link(href=commands, method=HttpMethod.POST),
        }
        if entity.is_tool:
            tool_commands = Endpoints.tool_commands_by_id(entity.id)
            links["updateFormatLabels"] = Link(href=tool_commands, method=HttpMethod.POST)
            links["repackage"] = Link(href=tool_commands, method=HttpMethod.POST)
            links["addVersion"] = Link(href=Endpoints.tool_versions_by_id(entity.id), method=HttpMethod.POST)
        return links

    def _is_link_allowed(self, rel: str, entity: Component) -> bool:
        match rel:
            case "self" | "download":
                return self._validator.can_read(entity)
            case "delete":
                return self._validator.can_delete(entity)
            case "impact":
                # read before an unpublish or a delete - both are the owner's
                return self._validator.can_update(entity)
            case "updateDescription":
                return self._validator.can_execute(entity, ComponentCommandType.UPDATE_DESCRIPTION)
            case "updateDomain":
                return self._validator.can_execute(entity, ComponentCommandType.UPDATE_DOMAIN)
            case "favorite":
                return self._validator.can_execute(entity, ComponentCommandType.ADD_FAVORITE)
            case "unfavorite":
                return self._validator.can_execute(entity, ComponentCommandType.REMOVE_FAVORITE)
            case "publish":
                return self._validator.can_execute(entity, ComponentCommandType.PUBLISH)
            case "unpublish":
                return self._validator.can_execute(entity, ComponentCommandType.UNPUBLISH)
            case "updateFormatLabels":
                return self._validator.can_execute_tool(entity, ToolCommandType.UPDATE_FORMAT_LABELS)
            case "repackage":
                return self._validator.can_execute_tool(entity, ToolCommandType.REPACKAGE)
            case "addVersion":
                return entity.is_tool and self._validator.can_update(entity)
            case _:
                return False
