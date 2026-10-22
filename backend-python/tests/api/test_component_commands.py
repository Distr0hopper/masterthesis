"""Which commands a viewer may run on a component, and which links they are offered -
the same answer, whatever the kind."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.api.link.component import ComponentLinkBuilder
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.application.commands.commands import ComponentCommandType, ToolCommandType
from app.domain.models.component import Component, ComponentKind, ComponentSource, ComponentStatus
from app.domain.models.tool import Tool
from app.domain.models.user import User
from app.domain.models.workflow import Workflow

OWNER = User(id=uuid.uuid4(), email="owner@example.com")
STRANGER = User(id=uuid.uuid4(), email="stranger@example.com")

OWNER_COMMAND_RELS = {"updateDescription", "updateDomain", "publish", "unpublish", "deprecate", "undeprecate"}
LOGGED_IN_COMMAND_RELS = {"favorite", "unfavorite"}
TOOL_COMMAND_RELS = {"updateFormatLabels", "repackage"}
OTHER_RELS = {"self", "download", "delete", "impact", "publishImpact", "addVersion"}


def component(kind: ComponentKind, source: ComponentSource = ComponentSource.MANUAL_UPLOAD) -> Component:
    """Published just now - still within its unpublish window, so every command applies."""
    c = Component(
        id=uuid.uuid4(),
        kind=kind,
        name="c",
        cwl_content="",
        created_by_id=OWNER.id,
        source=source,
        status=ComponentStatus.PUBLISHED,
        first_published_at=datetime.now(UTC),
    )
    if kind == ComponentKind.TOOL:
        c.tool = Tool()
    else:
        c.workflow = Workflow()
    return c


def command_rels(user: User | None, c: Component) -> set[str]:
    links = ComponentLinkBuilder(user)._filter_links(c)
    return set(links) - OTHER_RELS


def test_the_owner_is_offered_every_command_of_a_workflow() -> None:
    assert command_rels(OWNER, component(ComponentKind.WORKFLOW)) == OWNER_COMMAND_RELS | LOGGED_IN_COMMAND_RELS


def test_the_owner_is_offered_every_command_of_a_packaged_tool() -> None:
    tool = component(ComponentKind.TOOL, ComponentSource.AUTOMATED_PACKAGING)
    assert command_rels(OWNER, tool) == OWNER_COMMAND_RELS | LOGGED_IN_COMMAND_RELS | TOOL_COMMAND_RELS


def test_a_manual_tool_is_not_offered_repackage() -> None:
    expected = OWNER_COMMAND_RELS | LOGGED_IN_COMMAND_RELS | (TOOL_COMMAND_RELS - {"repackage"})
    assert command_rels(OWNER, component(ComponentKind.TOOL)) == expected


@pytest.mark.parametrize(
    ("source", "offered"),
    [(ComponentSource.MANUAL_UPLOAD, True), (ComponentSource.AUTOMATED_PACKAGING, False)],
)
def test_only_a_manual_tool_takes_an_uploaded_version(source: ComponentSource, offered: bool) -> None:
    tool = component(ComponentKind.TOOL, source)
    assert ("addVersion" in ComponentLinkBuilder(OWNER)._filter_links(tool)) is offered
    assert "addVersion" not in ComponentLinkBuilder(STRANGER)._filter_links(tool)


def test_an_uploaded_workflow_takes_an_uploaded_version_a_builder_one_does_not() -> None:
    uploaded = component(ComponentKind.WORKFLOW)
    links = ComponentLinkBuilder(OWNER)._filter_links(uploaded)
    assert links["addVersion"].href == f"/workflows/{uploaded.id}/versions"
    assert "addVersion" not in ComponentLinkBuilder(STRANGER)._filter_links(uploaded)

    # its versions come from saving the canvas
    from_builder = component(ComponentKind.WORKFLOW)
    from_builder.workflow.draft_id = uuid.uuid4()
    assert "addVersion" not in ComponentLinkBuilder(OWNER)._filter_links(from_builder)


@pytest.mark.parametrize("kind", list(ComponentKind))
def test_another_user_may_only_favorite(kind: ComponentKind) -> None:
    assert command_rels(STRANGER, component(kind)) == LOGGED_IN_COMMAND_RELS


@pytest.mark.parametrize("kind", list(ComponentKind))
def test_an_anonymous_viewer_is_offered_no_command(kind: ComponentKind) -> None:
    assert command_rels(None, component(kind)) == set()


@pytest.mark.parametrize("kind", list(ComponentKind))
def test_a_superseded_version_is_offered_neither_publish_nor_undeprecate(kind: ComponentKind) -> None:
    c = component(kind)
    # what the row is loaded with when a newer version of the lineage is published
    c.__dict__.update(superseded_by_id=uuid.uuid4(), superseded_by_version=2)
    assert command_rels(OWNER, c) == OWNER_COMMAND_RELS - {"publish", "undeprecate"} | LOGGED_IN_COMMAND_RELS | (
        TOOL_COMMAND_RELS - {"repackage"} if kind == ComponentKind.TOOL else set()
    )


def test_the_publish_impact_is_offered_wherever_publish_is() -> None:
    def rels(user: User | None, c: Component) -> set[str]:
        return set(ComponentLinkBuilder(user)._filter_links(c))

    c = component(ComponentKind.TOOL)
    assert "publishImpact" in rels(OWNER, c)
    assert "publishImpact" not in rels(STRANGER, c)
    c.__dict__.update(superseded_by_id=uuid.uuid4(), superseded_by_version=2)
    assert "publishImpact" not in rels(OWNER, c)


def test_unpublish_is_offered_only_within_the_window() -> None:
    c = component(ComponentKind.TOOL)
    assert "unpublish" in ComponentLinkBuilder(OWNER)._filter_links(c)
    c.first_published_at = datetime.now(UTC) - timedelta(days=2)
    # past it the version is only ever deprecated
    assert "unpublish" not in ComponentLinkBuilder(OWNER)._filter_links(c)
    assert "deprecate" in ComponentLinkBuilder(OWNER)._filter_links(c)


@pytest.mark.parametrize(
    ("status", "offered"),
    [(ComponentStatus.DRAFT, True), (ComponentStatus.PUBLISHED, False), (ComponentStatus.DEPRECATED, False)],
)
def test_delete_is_offered_only_on_drafts(status: ComponentStatus, offered: bool) -> None:
    c = component(ComponentKind.TOOL)
    c.status = status
    assert ("delete" in ComponentLinkBuilder(OWNER)._filter_links(c)) is offered
    assert "delete" not in ComponentLinkBuilder(STRANGER)._filter_links(c)


def test_command_links_point_at_the_commands_endpoint_of_the_kind() -> None:
    tool = component(ComponentKind.TOOL, ComponentSource.AUTOMATED_PACKAGING)
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
    tool = component(ComponentKind.TOOL, ComponentSource.AUTOMATED_PACKAGING)
    assert ComponentPermissionValidator(OWNER).can_execute_tool(tool, command)
    assert not ComponentPermissionValidator(STRANGER).can_execute_tool(tool, command)
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
