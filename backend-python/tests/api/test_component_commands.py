"""Which commands a viewer may run on a component, and which links they are offered -
the same answer, whatever the kind."""

import uuid

import pytest

from app.api.link.component import ComponentLinkBuilder
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.application.commands.commands import ComponentCommandType, ToolCommandType
from app.domain.models.component import Component, ComponentKind
from app.domain.models.tool import Tool
from app.domain.models.user import User
from app.domain.models.workflow import Workflow

OWNER = User(id=uuid.uuid4(), email="owner@example.com")
STRANGER = User(id=uuid.uuid4(), email="stranger@example.com")

OWNER_COMMAND_RELS = {"updateDescription", "updateDomain", "publish", "unpublish", "deprecate", "undeprecate"}
LOGGED_IN_COMMAND_RELS = {"favorite", "unfavorite"}
TOOL_COMMAND_RELS = {"updateFormatLabels", "repackage"}
OTHER_RELS = {"self", "download", "delete", "impact", "addVersion"}


def component(kind: ComponentKind) -> Component:
    c = Component(id=uuid.uuid4(), kind=kind, name="c", cwl_content="", created_by_id=OWNER.id)
    if kind == ComponentKind.TOOL:
        c.tool = Tool()
    else:
        c.workflow = Workflow()
    return c


def command_rels(user: User | None, c: Component) -> set[str]:
    links = ComponentLinkBuilder(user)._filter_links(c)
    return set(links) - OTHER_RELS


@pytest.mark.parametrize("kind", list(ComponentKind))
def test_the_owner_is_offered_every_command_of_the_kind(kind: ComponentKind) -> None:
    expected = OWNER_COMMAND_RELS | LOGGED_IN_COMMAND_RELS | (TOOL_COMMAND_RELS if kind == ComponentKind.TOOL else set())
    assert command_rels(OWNER, component(kind)) == expected


@pytest.mark.parametrize("kind", list(ComponentKind))
def test_another_user_may_only_favorite(kind: ComponentKind) -> None:
    assert command_rels(STRANGER, component(kind)) == LOGGED_IN_COMMAND_RELS


@pytest.mark.parametrize("kind", list(ComponentKind))
def test_an_anonymous_viewer_is_offered_no_command(kind: ComponentKind) -> None:
    assert command_rels(None, component(kind)) == set()


def test_command_links_point_at_the_commands_endpoint_of_the_kind() -> None:
    tool = component(ComponentKind.TOOL)
    links = ComponentLinkBuilder(OWNER)._filter_links(tool)
    assert links["publish"].href == f"/components/{tool.id}/commands"
    assert links["repackage"].href == f"/tools/{tool.id}/commands"
    assert all(links[rel].method == "POST" for rel in OWNER_COMMAND_RELS | TOOL_COMMAND_RELS)


@pytest.mark.parametrize("command", list(ComponentCommandType))
def test_component_commands_are_the_owners_except_favorites(command: ComponentCommandType) -> None:
    c = component(ComponentKind.WORKFLOW)
    is_favorite = command in (ComponentCommandType.ADD_FAVORITE, ComponentCommandType.REMOVE_FAVORITE)
    assert ComponentPermissionValidator(OWNER).can_execute(c, command)
    assert ComponentPermissionValidator(STRANGER).can_execute(c, command) is is_favorite
    assert not ComponentPermissionValidator(None).can_execute(c, command)


@pytest.mark.parametrize("command", list(ToolCommandType))
def test_tool_commands_are_the_owners_and_only_for_tools(command: ToolCommandType) -> None:
    assert ComponentPermissionValidator(OWNER).can_execute_tool(component(ComponentKind.TOOL), command)
    assert not ComponentPermissionValidator(STRANGER).can_execute_tool(component(ComponentKind.TOOL), command)
    assert not ComponentPermissionValidator(OWNER).can_execute_tool(component(ComponentKind.WORKFLOW), command)


def test_an_unknown_command_is_never_allowed() -> None:
    assert not ComponentPermissionValidator(OWNER).can_execute(component(ComponentKind.TOOL), "SELF_DESTRUCT")
    assert not ComponentPermissionValidator(OWNER).can_execute_tool(component(ComponentKind.TOOL), "PUBLISH")


def test_every_command_has_a_rel_of_its_own() -> None:
    # the link builder finds a command by its rel - two sharing one would shadow each other
    from app.application.service.components_service import COMPONENT_COMMANDS
    from app.application.service.tools_service import TOOL_COMMANDS

    rels = [spec.rel for spec in (*COMPONENT_COMMANDS.values(), *TOOL_COMMANDS.values())]
    assert len(rels) == len(set(rels))


def test_every_command_type_is_registered() -> None:
    from app.application.service.components_service import COMPONENT_COMMANDS
    from app.application.service.tools_service import TOOL_COMMANDS

    assert set(COMPONENT_COMMANDS) == set(ComponentCommandType)
    assert set(TOOL_COMMANDS) == set(ToolCommandType)
