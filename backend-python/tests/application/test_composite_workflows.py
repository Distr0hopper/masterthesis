"""The composite's workflow rules: publishing a whole tree, versioning on builder sync,
nesting without cycles, and locked steps on published workflows."""

import asyncio
import io
import uuid
import zipfile
from datetime import UTC, datetime

import pytest
from pydantic import TypeAdapter

from app.api.dto.component_variants import ComponentListItemDto
from app.api.dto.tool import ToolListItemDto
from app.api.dto.workflow import WorkflowListItemDto
from app.api.transformer.component_transformer import ComponentTransformer
from app.application.commands.commands import (
    ComponentCommand,
    ComponentCommandType,
    WorkflowStepCommand,
    WorkflowStepCommandType,
)
from app.application.exception.component_exceptions import InvalidCwlError
from app.application.exception.workflow_exceptions import (
    NestedWorkflowsNotReadyError,
    PublishedWorkflowStepsLockedError,
    UnpublishableWorkflowComponentsError,
    WorkflowCycleError,
    WorkflowHasUnpublishedComponentsError,
    WorkflowNotReadyToPublishError,
)
from app.application.service.components_service import ComponentsService
from app.application.service.tools_service import ToolsService
from app.application.service.workflows_service import ComponentConfig, StepBinding, WorkflowsService
from app.domain.models.component import Component, ComponentKind, ComponentStatus
from app.domain.models.tool import Tool
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep
from tests.application.fake_unit_of_work import FakeUnitOfWork

OWNER = uuid.uuid4()
STRANGER = uuid.uuid4()

PIPELINE = """
cwlVersion: v1.2
class: Workflow
inputs:
  data: File
outputs:
  result:
    type: File
    outputSource: step_a/out
steps: {}
"""


class FakeComponentsRepository:
    """In memory, with every tree already loaded - so load_tree is the identity."""

    def __init__(self, *components: Component):
        self.by_id: dict[uuid.UUID, Component] = {}
        self.renamed: list[tuple[str, str]] = []
        for component in components:
            self._store(component)

    def _store(self, component: Component) -> None:
        if component.id is None:
            component.id = uuid.uuid4()
        component.created_at = component.created_at or datetime.now(UTC)
        component.updated_at = datetime.now(UTC)
        self.by_id[component.id] = component

    async def find_by_id(self, component_id: uuid.UUID) -> Component | None:
        return self.by_id.get(component_id)

    find_by_id_fresh = find_by_id

    async def find_by_ids(self, ids: list[uuid.UUID]) -> list[Component]:
        return [self.by_id[i] for i in ids if i in self.by_id]

    async def find_versions_by_name(self, name: str) -> list[Component]:
        return sorted((c for c in self.by_id.values() if c.name == name), key=lambda c: c.version)

    async def find_latest_by_name(self, name: str) -> Component | None:
        versions = await self.find_versions_by_name(name)
        return versions[-1] if versions else None

    async def load_tree(self, root: Component) -> Component:
        return root

    async def rename_lineage(self, old_name: str, new_name: str) -> None:
        self.renamed.append((old_name, new_name))
        for component in self.by_id.values():
            if component.name == old_name:
                component.name = new_name

    async def find_all(self, status: ComponentStatus | None = None, kind: ComponentKind | None = None) -> list[Component]:
        return [c for c in self.by_id.values() if kind is None or c.kind == kind]

    async def add(self, component: Component) -> Component:
        self._store(component)
        return component

    async def add_all(self, components: list[Component]) -> None:
        for component in components:
            self._store(component)


class FakeWorkflowsRepository:
    def __init__(self, components: FakeComponentsRepository):
        self.components = components

    async def find_latest_by_draft_id(self, draft_id: uuid.UUID) -> Component | None:
        synced = [
            c
            for c in self.components.by_id.values()
            if c.workflow is not None and c.workflow.draft_id == draft_id
        ]
        return max(synced, key=lambda c: c.version, default=None)

    async def find_step_by_id(self, step_id: uuid.UUID) -> WorkflowStep | None:
        for component in self.components.by_id.values():
            for step in component.steps:
                if step.id == step_id:
                    return step
        return None

    async def add_step(self, step: WorkflowStep) -> WorkflowStep:
        step.component = self.components.by_id.get(step.component_id) if step.component_id else None
        return step


def tool(name: str, status: ComponentStatus = ComponentStatus.PUBLISHED, owner: uuid.UUID = OWNER) -> Component:
    component = Component(
        id=uuid.uuid4(), kind=ComponentKind.TOOL, name=name, cwl_content="class: CommandLineTool",
        status=status, created_by_id=owner,
    )
    component.tool = Tool(component_id=component.id)
    return component


def workflow(
    name: str,
    *children: Component,
    status: ComponentStatus = ComponentStatus.DRAFT,
    owner: uuid.UUID = OWNER,
    step_status: StepMatchStatus = StepMatchStatus.CONFIRMED,
    version: int = 1,
    draft_id: uuid.UUID | None = None,
) -> Component:
    component = Component(
        id=uuid.uuid4(), kind=ComponentKind.WORKFLOW, name=name, version=version, cwl_content=PIPELINE,
        status=status, created_by_id=owner,
    )
    component.workflow = Workflow(
        component_id=component.id,
        draft_id=draft_id,
        steps=[
            WorkflowStep(
                id=uuid.uuid4(),
                workflow_id=component.id,
                step_id=f"step_{i}",
                run_reference=f"{child.name}.cwl",
                step_order=i,
                component_id=child.id,
                component=child,
                match_status=step_status,
            )
            for i, child in enumerate(children)
        ],
    )
    for step in component.workflow.steps:
        step.workflow = component.workflow
    component.workflow.component = component
    return component


def services(*components: Component) -> tuple[ComponentsService, WorkflowsService, FakeComponentsRepository]:
    repository = FakeComponentsRepository(*components)
    uow = FakeUnitOfWork(components=repository, workflows=FakeWorkflowsRepository(repository))
    components_service = ComponentsService(uow, None)  # type: ignore[arg-type]
    tools_service = ToolsService(uow, components_service, None)  # type: ignore[arg-type]
    workflows_service = WorkflowsService(uow, components_service, tools_service)  # type: ignore[arg-type]
    return components_service, workflows_service, repository


def publish(components_service: ComponentsService, component: Component, publish_components: bool = False) -> Component:
    command = ComponentCommand(type=ComponentCommandType.PUBLISH, publish_components=publish_components)
    return asyncio.run(components_service.execute_command(component, command, OWNER))


# --- publishing a tree ------------------------------------------------------------------


def test_publishing_a_tool_just_flips_it() -> None:
    leaf = tool("t", ComponentStatus.DRAFT)
    components_service, _, _ = services(leaf)
    assert publish(components_service, leaf).status == ComponentStatus.PUBLISHED


def test_a_workflow_with_unconfirmed_steps_cannot_be_published() -> None:
    root = workflow("w", tool("t"), step_status=StepMatchStatus.SUGGESTED)
    components_service, _, _ = services(root)
    with pytest.raises(WorkflowNotReadyToPublishError):
        publish(components_service, root)


def test_a_nested_workflow_with_unconfirmed_steps_blocks_its_parent() -> None:
    inner = workflow("inner", tool("t"), step_status=StepMatchStatus.UNMATCHED)
    root = workflow("outer", inner)
    components_service, _, _ = services(root, inner)
    with pytest.raises(NestedWorkflowsNotReadyError) as err:
        publish(components_service, root)
    assert err.value.names == ["inner"]


def test_draft_children_at_any_depth_need_opting_in_and_are_then_published_together() -> None:
    deep_tool = tool("deep", ComponentStatus.DRAFT)
    inner = workflow("inner", deep_tool)
    root = workflow("outer", tool("public"), inner)
    components_service, _, _ = services(root, inner, deep_tool)

    with pytest.raises(WorkflowHasUnpublishedComponentsError) as err:
        publish(components_service, root)
    assert err.value.names == ["deep", "inner"]
    assert root.status == deep_tool.status == ComponentStatus.DRAFT

    publish(components_service, root, publish_components=True)
    assert root.status == inner.status == deep_tool.status == ComponentStatus.PUBLISHED
    # the refused attempt rolled back; the whole tree then went out in one commit
    assert (components_service.uow.commits, components_service.uow.rollbacks) == (1, 1)  # type: ignore[attr-defined]


def test_someone_elses_draft_anywhere_in_the_tree_blocks_publishing() -> None:
    root = workflow("outer", workflow("inner", tool("theirs", ComponentStatus.DRAFT, owner=STRANGER)))
    components_service, _, _ = services(root)
    with pytest.raises(UnpublishableWorkflowComponentsError) as err:
        publish(components_service, root, publish_components=True)
    assert err.value.names == ["theirs"]


# --- builder sync -----------------------------------------------------------------------


def sync(workflows_service: WorkflowsService, draft_id: uuid.UUID, *children: Component, name: str = "pipeline"):
    bindings = [StepBinding(step_id=f"step_{c.name}", run_reference=f"{c.name}.cwl", component_id=c.id) for c in children]

    async def in_unit_of_work() -> Component:
        async with workflows_service.uow:
            workflow = await workflows_service.upsert_from_draft(PIPELINE, bindings, name, draft_id, OWNER)
            await workflows_service.uow.commit()
        return workflow

    return asyncio.run(in_unit_of_work())


def test_first_sync_creates_version_one_with_confirmed_steps_and_ports() -> None:
    a = tool("a")
    _, workflows_service, _ = services(a)

    created = sync(workflows_service, uuid.uuid4(), a)

    assert (created.kind, created.version, created.status) == (ComponentKind.WORKFLOW, 1, ComponentStatus.DRAFT)
    assert [(s.component_id, s.match_status) for s in created.steps] == [(a.id, StepMatchStatus.CONFIRMED)]
    assert sorted((p.name, p.direction.value) for p in created.parameters) == [("data", "input"), ("result", "output")]


def test_resyncing_a_draft_version_updates_it_in_place() -> None:
    a, b = tool("a"), tool("b")
    _, workflows_service, repository = services(a, b)
    draft_id = uuid.uuid4()

    first = sync(workflows_service, draft_id, a)
    second = sync(workflows_service, draft_id, a, b)

    assert second.id == first.id and second.version == 1
    assert [s.component_id for s in second.steps] == [a.id, b.id]
    assert len(repository.by_id) == 3


def test_resyncing_a_published_version_creates_the_next_version() -> None:
    a, b = tool("a"), tool("b")
    _, workflows_service, _ = services(a, b)
    draft_id = uuid.uuid4()

    first = sync(workflows_service, draft_id, a)
    first.status = ComponentStatus.PUBLISHED
    second = sync(workflows_service, draft_id, a, b)

    assert second.id != first.id
    assert (second.name, second.version, second.status) == ("pipeline", 2, ComponentStatus.DRAFT)
    assert [s.component_id for s in first.steps] == [a.id]


def test_renaming_the_canvas_renames_the_whole_lineage() -> None:
    a = tool("a")
    _, workflows_service, repository = services(a)
    draft_id = uuid.uuid4()

    sync(workflows_service, draft_id, a, name="old")
    renamed = sync(workflows_service, draft_id, a, name="new")

    assert repository.renamed == [("old", "new")]
    assert renamed.name == "new"


def test_a_canvas_cannot_nest_a_workflow_that_contains_itself() -> None:
    draft_id = uuid.uuid4()
    own = workflow("pipeline", tool("a"), draft_id=draft_id)
    container = workflow("container", own)
    _, workflows_service, _ = services(own, container)

    with pytest.raises(WorkflowCycleError):
        sync(workflows_service, draft_id, container)


# --- steps ------------------------------------------------------------------------------


def test_a_step_can_nest_another_workflow() -> None:
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.UNMATCHED)
    child = workflow("inner", tool("b"))
    _, workflows_service, _ = services(parent, child)

    step = asyncio.run(workflows_service.update_step_component(parent.steps[0].id, child.id))

    assert (step.component_id, step.match_status) == (child.id, StepMatchStatus.SUGGESTED)


def test_a_step_cannot_nest_a_workflow_that_runs_its_own_workflow() -> None:
    parent = workflow("outer", tool("a"))
    child = workflow("inner", workflow("outer", tool("b"), version=2))
    _, workflows_service, _ = services(parent, child)

    with pytest.raises(WorkflowCycleError):
        asyncio.run(workflows_service.update_step_component(parent.steps[0].id, child.id))


def test_steps_of_a_published_workflow_are_locked() -> None:
    parent = workflow("outer", tool("a"), status=ComponentStatus.PUBLISHED)
    _, workflows_service, _ = services(parent)

    with pytest.raises(PublishedWorkflowStepsLockedError):
        asyncio.run(workflows_service.update_step_component(parent.steps[0].id, None))
    with pytest.raises(PublishedWorkflowStepsLockedError):
        asyncio.run(
            workflows_service.execute_step_command(parent.steps[0], WorkflowStepCommand(type=WorkflowStepCommandType.CONFIRM))
        )


def test_a_use_case_cannot_open_a_second_unit_of_work() -> None:
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.SUGGESTED)
    _, workflows_service, _ = services(parent)

    async def nested() -> None:
        async with workflows_service.uow:
            await workflows_service.update_step_component(parent.steps[0].id, None)

    with pytest.raises(RuntimeError, match="already open"):
        asyncio.run(nested())


# --- upload -----------------------------------------------------------------------------

UPLOAD_PIPELINE = """
cwlVersion: v1.2
class: Workflow
inputs:
  data: File
outputs:
  result:
    type: File
    outputSource: b/out
steps:
  a:
    run: a.cwl
    in: {inp: data}
    out: [out]
  b:
    run: b.cwl
    in: {inp: a/out}
    out: [out]
"""

UPLOAD_TOOL = """
cwlVersion: v1.2
class: CommandLineTool
baseCommand: echo
inputs:
  inp: File
outputs:
  out: File
"""


def test_a_failing_step_rolls_back_the_tools_created_before_it() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("pipeline.cwl", UPLOAD_PIPELINE)
        zf.writestr("a.cwl", UPLOAD_TOOL)
        # only found while creating b - after a is already created
        zf.writestr("b.cwl", UPLOAD_TOOL.replace("CommandLineTool", "Operation"))
    configs = {
        sid: ComponentConfig(step_id=sid, name=f"tool-{sid}", domains=["general"]) for sid in ("a", "b")
    }
    _, workflows_service, _ = services()

    with pytest.raises(InvalidCwlError):
        asyncio.run(
            workflows_service.create_from_upload(buffer.getvalue(), "x.zip", "wf", None, ["general"], configs, OWNER)
        )

    assert (workflows_service.uow.commits, workflows_service.uow.rollbacks) == (0, 1)  # type: ignore[attr-defined]


# --- the polymorphic DTO ----------------------------------------------------------------


def test_list_items_serialise_as_their_kind_and_parse_back_into_it() -> None:
    leaf, composite = tool("t"), workflow("w", tool("x"))
    for component in (leaf, composite):
        component.created_at = datetime.now(UTC)

    items = [ComponentTransformer.to_list_item(c, False, None) for c in (leaf, composite)]
    adapter = TypeAdapter(list[ComponentListItemDto])
    payload = adapter.dump_python(items, by_alias=True, mode="json")

    assert [p["kind"] for p in payload] == ["tool", "workflow"]
    assert payload[1]["stepCount"] == 1 and "stepCount" not in payload[0]
    parsed = adapter.validate_python(payload)
    assert [type(p) for p in parsed] == [ToolListItemDto, WorkflowListItemDto]
