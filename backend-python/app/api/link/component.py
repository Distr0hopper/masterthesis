from app.api.link.base import BaseLinkBuilder
from app.api.link.model import Link
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.util.endpoint import Endpoints
from app.api.util.http_method import HttpMethod
from app.application.commands.commands import ComponentCommandType, ToolCommandType
from app.application.service.components_service import COMPONENT_COMMANDS
from app.application.service.tools_service import TOOL_COMMANDS
from app.domain.models.component import Component


#: a command by the rel it is offered under - both families share one rel namespace
_COMPONENT_COMMAND_BY_REL: dict[str, ComponentCommandType] = {
    spec.rel: command for command, spec in COMPONENT_COMMANDS.items()
}
_TOOL_COMMAND_BY_REL: dict[str, ToolCommandType] = {spec.rel: command for command, spec in TOOL_COMMANDS.items()}


class ComponentLinkBuilder(BaseLinkBuilder[Component, ComponentPermissionValidator]):
    """The links of either kind - the shared ones on /components, plus the tool-only
    ones on /tools for a tool."""

    def _create_validator(self) -> ComponentPermissionValidator:
        return ComponentPermissionValidator(self.current_user)

    def _get_available_links(self, entity: Component) -> dict[str, Link]:
        links = {
            "self": Link(href=Endpoints.component_by_id(entity.id), method=HttpMethod.GET),
            "download": Link(href=Endpoints.component_download_by_id(entity.id), method=HttpMethod.GET),
            "delete": Link(href=Endpoints.component_by_id(entity.id), method=HttpMethod.DELETE),
            "impact": Link(href=Endpoints.component_impact_by_id(entity.id), method=HttpMethod.GET),
            "publishImpact": Link(href=Endpoints.component_publish_impact_by_id(entity.id), method=HttpMethod.GET),
        }
        # one POST link per declared command, offered under its rel
        commands = Endpoints.component_commands_by_id(entity.id)
        for spec in COMPONENT_COMMANDS.values():
            links[spec.rel] = Link(href=commands, method=HttpMethod.POST)
        if entity.is_tool:
            tool_commands = Endpoints.tool_commands_by_id(entity.id)
            for spec in TOOL_COMMANDS.values():
                links[spec.rel] = Link(href=tool_commands, method=HttpMethod.POST)
            links["addVersion"] = Link(href=Endpoints.tool_versions_by_id(entity.id), method=HttpMethod.POST)
        return links

    def _is_link_allowed(self, rel: str, entity: Component) -> bool:
        if (command := _COMPONENT_COMMAND_BY_REL.get(rel)) is not None:
            return self._validator.can_execute(entity, command)
        if (tool_command := _TOOL_COMMAND_BY_REL.get(rel)) is not None:
            return self._validator.can_execute_tool(entity, tool_command)
        match rel:
            case "self" | "download":
                return self._validator.can_read(entity)
            case "delete":
                return self._validator.can_delete(entity)
            case "impact":
                # read before an unpublish or a delete - both are the owner's
                return self._validator.can_update(entity)
            case "publishImpact":
                # read before a publish - offered wherever the publish itself is
                return self._validator.can_execute(entity, ComponentCommandType.PUBLISH)
            case "addVersion":
                # a packaged tool's versions come from its repo - see the repackage rel
                return entity.is_tool and not entity.is_packaged and self._validator.can_update(entity)
            case _:
                return False
