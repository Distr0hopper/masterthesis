"""The composite's workflow rules: publishing a whole tree, versioning on builder sync,
nesting without cycles, and locked steps on published workflows."""

import asyncio
import io
import uuid
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import TypeAdapter

from app.api.dto.component_variants import ComponentListItemDto
from app.api.dto.tool import ToolListItemDto
from app.api.dto.workflow import WorkflowListItemDto
from app.api.transformer.component_transformer import ComponentTransformer
from app.application.commands.commands import (
    ComponentCommand,
    ManualFormatLabel,
    ComponentCommandType,
    WorkflowStepCommand,
    WorkflowStepCommandType,
)
from app.application.exception.component_exceptions import (
    ComponentDeprecatedError,
    ComponentHasDeprecatedParentsError,
    ComponentHasLockedParentsError,
    ComponentHasPublicParentsError,
    ComponentsWithoutDomainsError,
    ComponentNotFoundError,
    ComponentUsedByOthersError,
    InvalidCwlError,
    OnlyDraftsCanBeDeletedError,
    PackagedToolCannotTakeUploadError,
    SupersededVersionError,
    UnpublishWindowClosedError,
)
from app.application.exception.workflow_exceptions import (
    InvalidComponentConfigError,
    InlineStepNotBindableError,
    NestedWorkflowsNotReadyError,
    PublishedWorkflowStepsLockedError,
    StepsEditedInBuilderError,
    UnpublishableWorkflowComponentsError,
    WorkflowCycleError,
    WorkflowHasUnpublishedComponentsError,
    WorkflowNotReadyToPublishError,
    WorkflowRunsDeprecatedComponentsError,
)
from app.application.service.components_service import ComponentsService
from app.application.service.tools_service import ToolsService
from app.application.service.workflows_service import ComponentConfig, StepBinding, WorkflowsService
from app.domain.models.component import Component, ComponentKind, ComponentSource, ComponentStatus
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.parameter import ParameterDirection
from app.domain.models.tool import Tool
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep
from app.domain.composite import lifecycle
from app.domain.composite.lifecycle import IllegalStatusTransitionError
from app.api.link.workflow_step import WorkflowStepLinkBuilder
from app.domain.models.user import User
from tests.application.fake_unit_of_work import FakeUnitOfWork

OWNER = uuid.uuid4()
OWNER_USER = User(id=OWNER, email="owner@example.com")
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

    async def find_all(
        self, statuses: frozenset[ComponentStatus] | None = None, kind: ComponentKind | None = None
    ) -> list[Component]:
        return [
            c
            for c in self.by_id.values()
            if (kind is None or c.kind == kind) and (statuses is None or c.status in statuses)
        ]

    async def add(self, component: Component) -> Component:
        self._store(component)
        return component

    async def add_all(self, components: list[Component]) -> None:
        for component in components:
            self._store(component)

    async def delete(self, component: Component) -> None:
        del self.by_id[component.id]

    async def find_ancestors(self, component_id: uuid.UUID) -> list[Component]:
        """Every workflow nesting this version, at any depth - scanned from the in-memory steps."""
        found: dict[uuid.UUID, Component] = {}
        frontier = {component_id}
        while frontier:
            parents = [
                c for c in self.by_id.values() if c.id not in found and any(s.component_id in frontier for s in c.steps)
            ]
            found.update((p.id, p) for p in parents)
            frontier = {p.id for p in parents}
        return list(found.values())


class FakeFavoritesRepository:
    async def delete_by_name(self, component_name: str) -> None:
        pass


class FakeWorkflowsRepository:
    def __init__(self, components: FakeComponentsRepository):
        self.components = components

    async def find_all_synced_from_draft(self, draft_id: uuid.UUID) -> list[Component]:
        synced = [
            c for c in self.components.by_id.values() if c.workflow is not None and c.workflow.draft_id == draft_id
        ]
        return sorted(synced, key=lambda c: c.version)

    async def find_latest_by_draft_id(self, draft_id: uuid.UUID) -> Component | None:
        synced = [
            c for c in self.components.by_id.values() if c.workflow is not None and c.workflow.draft_id == draft_id
        ]
        return max(synced, key=lambda c: c.version, default=None)

    async def find_steps_by_component_id(self, component_id: uuid.UUID) -> list[WorkflowStep]:
        return [s for c in self.components.by_id.values() for s in c.steps if s.component_id == component_id]

    async def add_steps(self, steps: list[WorkflowStep], workflows: list[Component]) -> None:
        pass

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
        id=uuid.uuid4(),
        kind=ComponentKind.TOOL,
        name=name,
        cwl_content="class: CommandLineTool",
        status=status,
        created_by_id=owner,
        # a public one was published just now - still within its unpublish window
        first_published_at=None if status == ComponentStatus.DRAFT else datetime.now(UTC),
        # every public component has one - see lifecycle.without_domains
        domains=[ComponentDomain(domain="other")],
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
        id=uuid.uuid4(),
        kind=ComponentKind.WORKFLOW,
        name=name,
        version=version,
        cwl_content=PIPELINE,
        status=status,
        created_by_id=owner,
        first_published_at=None if status == ComponentStatus.DRAFT else datetime.now(UTC),
        domains=[ComponentDomain(domain="other")],
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
    uow = FakeUnitOfWork(
        components=repository, workflows=FakeWorkflowsRepository(repository), favorites=FakeFavoritesRepository()
    )
    components_service = ComponentsService(uow, None)  # type: ignore[arg-type]
    tools_service = ToolsService(uow, components_service, None)  # type: ignore[arg-type]
    workflows_service = WorkflowsService(uow, components_service, tools_service)  # type: ignore[arg-type]
    return components_service, workflows_service, repository


def publish(components_service: ComponentsService, component: Component, publish_components: bool = False) -> Component:
    command = ComponentCommand(type=ComponentCommandType.PUBLISH, publish_components=publish_components)
    return asyncio.run(components_service.execute_command(component, command, OWNER))


def unpublish(
    components_service: ComponentsService, component: Component, unpublish_parents: bool = False
) -> Component:
    command = ComponentCommand(type=ComponentCommandType.UNPUBLISH, unpublish_parents=unpublish_parents)
    return asyncio.run(components_service.execute_command(component, command, OWNER))


# --- publishing a tree ------------------------------------------------------------------


def test_publishing_a_tool_just_flips_it() -> None:
    leaf = tool("t", ComponentStatus.DRAFT)
    components_service, _, _ = services(leaf)
    assert publish(components_service, leaf).status == ComponentStatus.PUBLISHED


def test_publishing_a_new_version_deprecates_the_published_older_ones_for_good() -> None:
    v1, v2, v3 = tool("t"), tool("t", ComponentStatus.DEPRECATED), tool("t", ComponentStatus.DRAFT)
    v2.version, v3.version = 2, 3
    v2.deprecation_note = "broken"
    other = tool("other")
    components_service, _, _ = services(v1, v2, v3, other)

    publish(components_service, v3)

    assert (v1.status, v1.deprecation_note) == (ComponentStatus.DEPRECATED, "Superseded by v3")
    # already deprecated - its own note stays
    assert (v2.status, v2.deprecation_note) == (ComponentStatus.DEPRECATED, "broken")
    assert other.status == ComponentStatus.PUBLISHED

    # taking v3 back down doesn't put v1 on offer again
    unpublish(components_service, v3)
    assert v1.status == ComponentStatus.DEPRECATED


def test_the_publish_impact_names_exactly_what_the_publish_then_deprecates() -> None:
    old_tool, new_tool = tool("t"), tool("t", ComponentStatus.DRAFT)
    new_tool.version = 2
    old_wf = workflow("w", old_tool, status=ComponentStatus.PUBLISHED)
    new_wf = workflow("w", new_tool, version=2)
    components_service, _, _ = services(old_wf, new_wf, old_tool, new_tool)

    impact = asyncio.run(components_service.get_publish_impact(new_wf, OWNER))

    # the workflow's own older version, and the one of the draft tool published along
    assert [(s.component.name, s.component.version, s.superseded_by.version) for s in impact] == [
        ("t", 1, 2),
        ("w", 1, 2),
    ]
    # old_wf runs the old tool - it keeps working, so it is just counted
    assert [s.workflow_count for s in impact] == [1, 0]
    # a preview changes nothing
    assert old_tool.status == old_wf.status == ComponentStatus.PUBLISHED

    publish(components_service, new_wf, publish_components=True)
    assert old_tool.status == old_wf.status == ComponentStatus.DEPRECATED


def test_publishing_a_first_version_supersedes_nothing() -> None:
    leaf = tool("t", ComponentStatus.DRAFT)
    components_service, _, _ = services(leaf)
    assert asyncio.run(components_service.get_publish_impact(leaf, OWNER)) == []


def test_an_older_version_cannot_be_published_next_to_a_newer_published_one() -> None:
    v1, v2 = tool("t", ComponentStatus.DRAFT), tool("t")
    v2.version = 2
    components_service, _, _ = services(v1, v2)

    with pytest.raises(SupersededVersionError):
        publish(components_service, v1)
    assert v1.status == ComponentStatus.DRAFT


def test_a_superseded_version_cannot_be_undeprecated_until_the_newer_one_is_down() -> None:
    v1, v2 = tool("t", ComponentStatus.DEPRECATED), tool("t")
    v2.version = 2
    components_service, _, _ = services(v1, v2)

    with pytest.raises(SupersededVersionError):
        undeprecate(components_service, v1)
    assert v1.status == ComponentStatus.DEPRECATED

    unpublish(components_service, v2)
    undeprecate(components_service, v1)
    assert v1.status == ComponentStatus.PUBLISHED


def test_a_superseded_draft_is_not_published_along_with_a_workflow() -> None:
    old = tool("t", ComponentStatus.DRAFT)
    new = tool("t")
    new.version = 2
    root = workflow("w", old)
    components_service, _, _ = services(root, old, new)

    with pytest.raises(SupersededVersionError):
        publish(components_service, root, publish_components=True)
    assert root.status == old.status == ComponentStatus.DRAFT


def test_drafts_published_along_with_a_workflow_supersede_their_older_versions() -> None:
    old = tool("t")
    new = tool("t", ComponentStatus.DRAFT)
    new.version = 2
    root = workflow("w", new)
    components_service, _, _ = services(root, old, new)

    publish(components_service, root, publish_components=True)

    assert old.status == ComponentStatus.DEPRECATED


def test_nothing_goes_public_without_a_domain() -> None:
    leaf = tool("t", ComponentStatus.DRAFT)
    leaf.domains = []
    components_service, _, _ = services(leaf)

    with pytest.raises(ComponentsWithoutDomainsError) as err:
        publish(components_service, leaf)
    assert err.value.labels == ["t v1"]
    assert leaf.status == ComponentStatus.DRAFT


def test_a_draft_published_along_needs_a_domain_too() -> None:
    child = tool("child", ComponentStatus.DRAFT)
    child.domains = []
    root = workflow("w", child)
    components_service, _, _ = services(root, child)

    with pytest.raises(ComponentsWithoutDomainsError) as err:
        publish(components_service, root, publish_components=True)
    assert err.value.labels == ["child v1"]
    assert root.status == child.status == ComponentStatus.DRAFT


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


# --- taking a version out of public view -------------------------------------------------


def test_bug1_unpublishing_a_tool_another_users_public_workflow_runs_is_refused() -> None:
    shared = tool("t")
    theirs = workflow("theirs", shared, status=ComponentStatus.PUBLISHED, owner=STRANGER)
    components_service, _, _ = services(shared, theirs)

    with pytest.raises(ComponentUsedByOthersError):
        unpublish(components_service, shared)

    assert shared.status == theirs.status == ComponentStatus.PUBLISHED
    assert components_service.uow.commits == 0  # type: ignore[attr-defined]


def test_a_public_version_is_never_deleted() -> None:
    # others may run, nest or cite it - it is deprecated instead
    published, deprecated = tool("published"), tool("deprecated", ComponentStatus.DEPRECATED)
    components_service, _, repository = services(published, deprecated)

    for public in (published, deprecated):
        with pytest.raises(OnlyDraftsCanBeDeletedError):
            asyncio.run(components_service.remove(public, OWNER))
        assert public.id in repository.by_id
    assert components_service.uow.commits == 0  # type: ignore[attr-defined]


def test_unpublishing_takes_own_public_ancestors_along_only_when_opted_into() -> None:
    leaf = tool("t")
    parent = workflow("parent", leaf, status=ComponentStatus.PUBLISHED)
    grandparent = workflow("grandparent", parent, status=ComponentStatus.PUBLISHED)
    components_service, _, _ = services(leaf, parent, grandparent)

    with pytest.raises(ComponentHasPublicParentsError) as err:
        unpublish(components_service, leaf)
    assert err.value.workflows == ["grandparent v1", "parent v1"]
    assert leaf.status == parent.status == grandparent.status == ComponentStatus.PUBLISHED

    unpublish(components_service, leaf, unpublish_parents=True)
    assert leaf.status == parent.status == grandparent.status == ComponentStatus.DRAFT
    assert components_service.uow.commits == 1  # type: ignore[attr-defined]


def test_unpublishing_a_draft_is_a_no_op() -> None:
    leaf = tool("t", ComponentStatus.DRAFT)
    components_service, _, _ = services(leaf)
    assert unpublish(components_service, leaf).status == ComponentStatus.DRAFT


def test_another_users_public_grandparent_blocks_a_delete() -> None:
    # a draft run by public workflows only exists in data from before the invariant - still guarded
    leaf = tool("t", ComponentStatus.DRAFT)
    parent = workflow("parent", leaf, status=ComponentStatus.PUBLISHED)
    theirs = workflow("theirs", parent, status=ComponentStatus.PUBLISHED, owner=STRANGER)
    components_service, _, repository = services(leaf, parent, theirs)

    with pytest.raises(ComponentUsedByOthersError):
        asyncio.run(components_service.remove(leaf, OWNER, unpublish_parents=True))

    assert leaf.id in repository.by_id
    assert parent.status == theirs.status == ComponentStatus.PUBLISHED
    assert parent.steps[0].match_status == StepMatchStatus.CONFIRMED
    assert components_service.uow.commits == 0  # type: ignore[attr-defined]


def test_a_version_past_its_unpublish_window_is_only_deprecated() -> None:
    leaf = tool("t")
    leaf.first_published_at = datetime.now(UTC) - timedelta(days=2)
    components_service, _, _ = services(leaf)

    with pytest.raises(UnpublishWindowClosedError):
        unpublish(components_service, leaf)
    assert leaf.status == ComponentStatus.PUBLISHED

    deprecate(components_service, leaf, "use v2")
    assert leaf.status == ComponentStatus.DEPRECATED


def test_own_parents_past_their_window_block_unpublishing() -> None:
    leaf = tool("t")
    parent = workflow("parent", leaf, status=ComponentStatus.PUBLISHED)
    parent.first_published_at = datetime.now(UTC) - timedelta(days=2)
    components_service, _, _ = services(leaf, parent)

    with pytest.raises(ComponentHasLockedParentsError):
        unpublish(components_service, leaf, unpublish_parents=True)
    assert leaf.status == parent.status == ComponentStatus.PUBLISHED


def test_unpublishing_within_the_window_makes_a_normal_draft_again() -> None:
    leaf = tool("t")
    components_service, _, _ = services(leaf)

    unpublish(components_service, leaf)

    # as if never published - and deletable now
    assert (leaf.status, leaf.first_published_at) == (ComponentStatus.DRAFT, None)
    asyncio.run(components_service.remove(leaf, OWNER))


# --- deprecation ------------------------------------------------------------------------


def deprecate(components_service: ComponentsService, component: Component, note: str | None = None) -> Component:
    command = ComponentCommand(type=ComponentCommandType.DEPRECATE, deprecation_note=note)
    return asyncio.run(components_service.execute_command(component, command, OWNER))


def undeprecate(components_service: ComponentsService, component: Component) -> Component:
    return asyncio.run(
        components_service.execute_command(component, ComponentCommand(type=ComponentCommandType.UNDEPRECATE), OWNER)
    )


def test_deprecating_retracts_a_version_others_run_without_breaking_them() -> None:
    shared = tool("t")
    theirs = workflow("theirs", shared, status=ComponentStatus.PUBLISHED, owner=STRANGER)
    components_service, _, _ = services(shared, theirs)

    deprecate(components_service, shared, "  wrong CRS handling, use v3  ")

    assert (shared.status, shared.deprecation_note) == (ComponentStatus.DEPRECATED, "wrong CRS handling, use v3")
    assert theirs.status == ComponentStatus.PUBLISHED
    undeprecate(components_service, shared)
    assert (shared.status, shared.deprecation_note) == (ComponentStatus.PUBLISHED, None)
    assert components_service.uow.commits == 2  # type: ignore[attr-defined]


def test_a_draft_cannot_be_deprecated() -> None:
    draft_tool = tool("t", ComponentStatus.DRAFT)
    components_service, _, _ = services(draft_tool)
    with pytest.raises(IllegalStatusTransitionError):
        deprecate(components_service, draft_tool)
    assert draft_tool.status == ComponentStatus.DRAFT


def test_a_deprecated_version_is_undeprecated_before_it_can_be_unpublished() -> None:
    old = tool("t", ComponentStatus.DEPRECATED)
    components_service, _, _ = services(old)
    with pytest.raises(IllegalStatusTransitionError):
        unpublish(components_service, old, unpublish_parents=True)
    assert old.status == ComponentStatus.DEPRECATED


def test_an_own_deprecated_ancestor_blocks_unpublish_and_delete_and_changes_nothing() -> None:
    leaf = tool("t")
    parent = workflow("parent", leaf, status=ComponentStatus.PUBLISHED)
    grandparent = workflow("grandparent", parent, status=ComponentStatus.DEPRECATED)
    components_service, _, repository = services(leaf, parent, grandparent)

    with pytest.raises(ComponentHasDeprecatedParentsError) as err:
        unpublish(components_service, leaf, unpublish_parents=True)
    assert err.value.workflows == ["grandparent v1"]
    # and a public version is never deleted in the first place
    with pytest.raises(OnlyDraftsCanBeDeletedError):
        asyncio.run(components_service.remove(leaf, OWNER, unpublish_parents=True))

    assert leaf.id in repository.by_id
    assert (leaf.status, parent.status, grandparent.status) == (
        ComponentStatus.PUBLISHED,
        ComponentStatus.PUBLISHED,
        ComponentStatus.DEPRECATED,
    )
    assert parent.steps[0].match_status == StepMatchStatus.CONFIRMED
    assert components_service.uow.commits == 0  # type: ignore[attr-defined]


def test_publishing_a_workflow_that_runs_a_deprecated_version_is_refused() -> None:
    old = tool("old", ComponentStatus.DEPRECATED, owner=STRANGER)
    old.deprecation_note = "use v2"
    root = workflow("w", old)
    components_service, _, _ = services(root, old)

    with pytest.raises(WorkflowRunsDeprecatedComponentsError) as err:
        publish(components_service, root, publish_components=True)

    assert err.value.components == ["old v1 (use v2)"]
    assert root.status == ComponentStatus.DRAFT and old.status == ComponentStatus.DEPRECATED


def test_an_unpublished_workflow_cannot_be_republished_over_a_since_deprecated_child() -> None:
    # documented consequence: republishing would give the deprecated version a new dependent
    leaf = tool("t")
    root = workflow("w", leaf, status=ComponentStatus.PUBLISHED)
    components_service, _, _ = services(leaf, root)

    deprecate(components_service, leaf)
    unpublish(components_service, root)

    with pytest.raises(WorkflowRunsDeprecatedComponentsError):
        publish(components_service, root)
    assert root.status == ComponentStatus.DRAFT


# --- builder sync -----------------------------------------------------------------------


def sync(workflows_service: WorkflowsService, draft_id: uuid.UUID, *children: Component, name: str = "pipeline"):
    bindings = [
        StepBinding(step_id=f"step_{c.name}", run_reference=f"{c.name}.cwl", component_id=c.id) for c in children
    ]

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


def test_the_first_sync_sets_no_domains_the_owner_picks_them_before_publishing() -> None:
    a = tool("a")
    _, workflows_service, _ = services(a)

    created = sync(workflows_service, uuid.uuid4(), a)

    assert created.domains == []


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


def test_saving_the_canvas_after_an_early_unpublish_updates_it_in_place() -> None:
    # unpublished within its window, v1 is a plain draft again - the next save rewrites it
    a, b = tool("a"), tool("b")
    _, workflows_service, _ = services(a, b)
    draft_id = uuid.uuid4()
    first = sync(workflows_service, draft_id, a)
    lifecycle.mark_published([first])
    lifecycle.mark_draft([first])

    second = sync(workflows_service, draft_id, a, b)

    assert second.id == first.id and second.version == 1
    assert [s.component_id for s in second.steps] == [a.id, b.id]


def test_deleting_a_canvas_with_its_workflows_keeps_the_public_versions() -> None:
    draft_id = uuid.uuid4()
    public = workflow("w", tool("a"), status=ComponentStatus.PUBLISHED, draft_id=draft_id)
    fresh = workflow("w", tool("a"), version=2, draft_id=draft_id)
    components_service, _, repository = services(public, fresh)

    async def in_unit_of_work() -> int:
        async with components_service.uow:
            removed = await components_service.remove_synced_from_draft(draft_id, OWNER)
            await components_service.uow.commit()
        return removed

    # only drafts are ever deleted - the published v1 stays, just without its canvas
    assert asyncio.run(in_unit_of_work()) == 1
    assert public.id in repository.by_id and fresh.id not in repository.by_id


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

    step = asyncio.run(workflows_service.update_step_component(parent.steps[0].id, child.id, OWNER))

    assert (step.component_id, step.match_status) == (child.id, StepMatchStatus.SUGGESTED)


def test_a_step_cannot_nest_a_workflow_that_runs_its_own_workflow() -> None:
    parent = workflow("outer", tool("a"))
    child = workflow("inner", workflow("outer", tool("b"), version=2))
    _, workflows_service, _ = services(parent, child)

    with pytest.raises(WorkflowCycleError):
        asyncio.run(workflows_service.update_step_component(parent.steps[0].id, child.id, OWNER))


def test_steps_of_a_published_workflow_are_locked() -> None:
    parent = workflow("outer", tool("a"), status=ComponentStatus.PUBLISHED)
    _, workflows_service, _ = services(parent)

    with pytest.raises(PublishedWorkflowStepsLockedError):
        asyncio.run(workflows_service.update_step_component(parent.steps[0].id, None, OWNER))
    with pytest.raises(PublishedWorkflowStepsLockedError):
        asyncio.run(
            workflows_service.execute_step_command(
                parent.steps[0], WorkflowStepCommand(type=WorkflowStepCommandType.CONFIRM)
            )
        )


def test_a_builder_workflows_steps_change_on_its_canvas_only() -> None:
    # its step lost its component when that was deleted - the fix belongs on the canvas
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.UNMATCHED, draft_id=uuid.uuid4())
    replacement = tool("b")
    _, workflows_service, _ = services(parent, replacement)
    step = parent.steps[0]

    with pytest.raises(StepsEditedInBuilderError):
        asyncio.run(workflows_service.update_step_component(step.id, replacement.id, OWNER))
    with pytest.raises(StepsEditedInBuilderError):
        asyncio.run(
            workflows_service.execute_step_command(step, WorkflowStepCommand(type=WorkflowStepCommandType.CONFIRM))
        )
    assert step.match_status == StepMatchStatus.UNMATCHED

    links = WorkflowStepLinkBuilder(OWNER_USER)._filter_links(step)
    assert "update" not in links and "confirm" not in links


def test_once_its_canvas_is_deleted_a_builder_workflow_is_edited_on_its_page() -> None:
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.UNMATCHED, draft_id=None)
    replacement = tool("b")
    _, workflows_service, _ = services(parent, replacement)

    asyncio.run(workflows_service.update_step_component(parent.steps[0].id, replacement.id, OWNER))

    assert parent.steps[0].component_id == replacement.id
    assert set(WorkflowStepLinkBuilder(OWNER_USER)._filter_links(parent.steps[0])) == {"update", "confirm"}


def test_after_an_early_unpublish_its_steps_are_editable_again() -> None:
    published_tool = tool("a")
    parent = workflow("outer", published_tool, step_status=StepMatchStatus.SUGGESTED)
    other = tool("b")
    lifecycle.mark_published([parent])
    lifecycle.mark_draft([parent])
    _, workflows_service, _ = services(parent, other)

    asyncio.run(workflows_service.update_step_component(parent.steps[0].id, other.id, OWNER))

    assert parent.steps[0].component_id == other.id
    links = WorkflowStepLinkBuilder(OWNER_USER)._filter_links(parent.steps[0])
    assert "update" in links and "confirm" in links


def test_a_new_step_cannot_run_a_deprecated_version() -> None:
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.UNMATCHED)
    old = tool("old", ComponentStatus.DEPRECATED)
    _, workflows_service, _ = services(parent, old)

    with pytest.raises(ComponentDeprecatedError):
        asyncio.run(workflows_service.update_step_component(parent.steps[0].id, old.id, OWNER))
    assert parent.steps[0].match_status == StepMatchStatus.UNMATCHED


def test_someone_elses_draft_is_unknown_to_a_step() -> None:
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.UNMATCHED)
    theirs = tool("theirs", ComponentStatus.DRAFT, owner=STRANGER)
    _, workflows_service, _ = services(parent, theirs)

    with pytest.raises(ComponentNotFoundError):
        asyncio.run(workflows_service.update_step_component(parent.steps[0].id, theirs.id, OWNER))


def test_an_inline_step_cannot_be_bound() -> None:
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.INLINE)
    other = tool("b")
    _, workflows_service, _ = services(parent, other)

    with pytest.raises(InlineStepNotBindableError):
        asyncio.run(workflows_service.update_step_component(parent.steps[0].id, other.id, OWNER))
    assert parent.steps[0].match_status == StepMatchStatus.INLINE


def test_clearing_an_empty_step_again_is_fine() -> None:
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.UNMATCHED)
    _, workflows_service, _ = services(parent)

    step = asyncio.run(workflows_service.update_step_component(parent.steps[0].id, None, OWNER))
    step = asyncio.run(workflows_service.update_step_component(parent.steps[0].id, None, OWNER))

    assert (step.component_id, step.match_status) == (None, StepMatchStatus.UNMATCHED)


def test_a_use_case_cannot_open_a_second_unit_of_work() -> None:
    parent = workflow("outer", tool("a"), step_status=StepMatchStatus.SUGGESTED)
    _, workflows_service, _ = services(parent)

    async def nested() -> None:
        async with workflows_service.uow:
            await workflows_service.update_step_component(parent.steps[0].id, None, OWNER)

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


def test_an_upload_cannot_reuse_a_deprecated_version() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("pipeline.cwl", UPLOAD_PIPELINE)
        zf.writestr("a.cwl", UPLOAD_TOOL)
        zf.writestr("b.cwl", UPLOAD_TOOL)
    old = tool("old", ComponentStatus.DEPRECATED)
    configs = {
        "a": ComponentConfig(step_id="a", reuse_component_id=old.id),
        "b": ComponentConfig(step_id="b", name="tool-b", domains=["general"]),
    }
    _, workflows_service, repository = services(old)

    with pytest.raises(ComponentDeprecatedError):
        asyncio.run(
            workflows_service.create_from_upload(buffer.getvalue(), "x.zip", "wf", None, ["general"], configs, OWNER)
        )

    assert list(repository.by_id) == [old.id]
    assert workflows_service.uow.commits == 0  # type: ignore[attr-defined]


def test_a_failing_step_rolls_back_the_tools_created_before_it() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("pipeline.cwl", UPLOAD_PIPELINE)
        zf.writestr("a.cwl", UPLOAD_TOOL)
        # only found while creating b - after a is already created
        zf.writestr("b.cwl", UPLOAD_TOOL.replace("CommandLineTool", "Operation"))
    configs = {sid: ComponentConfig(step_id=sid, name=f"tool-{sid}", domains=["general"]) for sid in ("a", "b")}
    _, workflows_service, _ = services()

    with pytest.raises(InvalidCwlError):
        asyncio.run(
            workflows_service.create_from_upload(buffer.getvalue(), "x.zip", "wf", None, ["general"], configs, OWNER)
        )

    assert (workflows_service.uow.commits, workflows_service.uow.rollbacks) == (0, 1)  # type: ignore[attr-defined]


def upload_zip(a_tool: str = UPLOAD_TOOL, b_tool: str = UPLOAD_TOOL) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("pipeline.cwl", UPLOAD_PIPELINE)
        zf.writestr("a.cwl", a_tool)
        zf.writestr("b.cwl", b_tool)
    return buffer.getvalue()


def uploaded_v1() -> tuple[Component, Component, Component]:
    """An uploaded workflow 'wf' v1 whose steps a and b run the owner's tools tool-a and tool-b."""
    tool_a, tool_b = tool("tool-a"), tool("tool-b")
    tool_a.cwl_content = tool_b.cwl_content = UPLOAD_TOOL
    v1 = workflow("wf", tool_a, tool_b, status=ComponentStatus.PUBLISHED)
    v1.workflow.steps[0].step_id, v1.workflow.steps[1].step_id = "a", "b"
    return v1, tool_a, tool_b


CHANGED_TOOL = UPLOAD_TOOL.replace("baseCommand: echo", "baseCommand: cat")


def test_the_preview_of_a_new_version_reports_what_each_step_ran_before() -> None:
    v1, tool_a, tool_b = uploaded_v1()
    _, workflows_service, _ = services(v1, tool_a, tool_b)

    preview = asyncio.run(workflows_service.parse_workflow_upload(upload_zip(a_tool=CHANGED_TOOL), "x.zip", v1, OWNER))

    previous = {p.step_id: p.previous for p in preview.component_previews}
    assert previous["a"] is not None and previous["b"] is not None
    assert (previous["a"].component.id, previous["a"].cwl_changed, previous["a"].can_add_version) == (
        tool_a.id,
        True,
        True,
    )
    # reformatting is no change - compared as parsed YAML
    assert previous["b"].cwl_changed is False
    # someone else's tool can't take the step as its next version
    other = asyncio.run(workflows_service.parse_workflow_upload(upload_zip(), "x.zip", v1, STRANGER))
    assert all(not p.previous.can_add_version for p in other.component_previews if p.previous)


def test_an_uploaded_new_version_keeps_the_lineage_and_versions_a_changed_tool() -> None:
    v1, tool_a, tool_b = uploaded_v1()
    _, workflows_service, repository = services(v1, tool_a, tool_b)
    configs = {
        "a": ComponentConfig(step_id="a", new_version_of_id=tool_a.id),
        "b": ComponentConfig(step_id="b", reuse_component_id=tool_b.id),
    }

    v2 = asyncio.run(
        workflows_service.add_version_from_upload(v1, upload_zip(a_tool=CHANGED_TOOL), "x.zip", None, configs, OWNER)
    )

    assert (v2.name, v2.version, v2.status) == ("wf", 2, ComponentStatus.DRAFT)
    step_a, step_b = v2.steps
    # tool-a's next version, a draft until published with the workflow
    assert (step_a.component.name, step_a.component.version, step_a.component.status) == (
        "tool-a",
        2,
        ComponentStatus.DRAFT,
    )
    assert step_b.component_id == tool_b.id
    assert workflows_service.uow.commits == 1  # type: ignore[attr-defined]


def test_a_builder_workflow_takes_no_uploaded_version() -> None:
    v1, tool_a, tool_b = uploaded_v1()
    v1.workflow.draft_id = uuid.uuid4()
    _, workflows_service, _ = services(v1, tool_a, tool_b)
    configs = {sid: ComponentConfig(step_id=sid, reuse_component_id=tool_b.id) for sid in ("a", "b")}

    with pytest.raises(StepsEditedInBuilderError):
        asyncio.run(workflows_service.add_version_from_upload(v1, upload_zip(), "x.zip", None, configs, OWNER))


@pytest.mark.parametrize("problem", ["someone else's", "packaged", "twice"])
def test_a_step_versions_only_one_of_the_actors_uploaded_tools_once(problem: str) -> None:
    v1, tool_a, tool_b = uploaded_v1()
    target = tool_a
    if problem == "someone else's":
        target = tool("theirs", owner=STRANGER)
    if problem == "packaged":
        target.source = ComponentSource.AUTOMATED_PACKAGING
    _, workflows_service, _ = services(v1, tool_a, tool_b, target)
    configs = {
        "a": ComponentConfig(step_id="a", new_version_of_id=target.id),
        "b": (
            ComponentConfig(step_id="b", new_version_of_id=target.id)
            if problem == "twice"
            else ComponentConfig(step_id="b", reuse_component_id=tool_b.id)
        ),
    }

    with pytest.raises((InvalidComponentConfigError, PackagedToolCannotTakeUploadError)):
        asyncio.run(workflows_service.add_version_from_upload(v1, upload_zip(), "x.zip", None, configs, OWNER))
    assert workflows_service.uow.commits == 0  # type: ignore[attr-defined]


def test_an_upload_creates_its_tools_and_the_workflow_as_version_one() -> None:
    configs = {sid: ComponentConfig(step_id=sid, name=f"tool-{sid}", domains=["other"]) for sid in ("a", "b")}
    _, workflows_service, _ = services()

    wf = asyncio.run(workflows_service.create_from_upload(upload_zip(), "x.zip", "wf", None, ["other"], configs, OWNER))

    assert (wf.name, wf.version, wf.status) == ("wf", 1, ComponentStatus.DRAFT)
    assert [(s.step_id, s.component.name, s.component.version) for s in wf.steps] == [
        ("a", "tool-a", 1),
        ("b", "tool-b", 1),
    ]
    assert all(s.match_status == StepMatchStatus.CONFIRMED for s in wf.steps)
    assert workflows_service.uow.commits == 1  # type: ignore[attr-defined]


INLINE_PIPELINE = """
cwlVersion: v1.2
class: Workflow
inputs:
  data: File
outputs:
  result:
    type: File
    outputSource: a/out
steps:
  a:
    run:
      class: CommandLineTool
      baseCommand: cat
      inputs:
        inp:
          type: File
      outputs:
        out:
          type: File
    in: {inp: data}
    out: [out]
"""


def test_an_inline_step_versioning_a_tool_runs_a_file_named_after_that_tool() -> None:
    # the stored pipeline swaps the inline body for a run: reference - named after the
    # lineage the step joins, not after anything in the upload
    tool_a = tool("Tool A")
    v1 = workflow("wf", tool_a, status=ComponentStatus.PUBLISHED)
    v1.workflow.steps[0].step_id = "a"
    _, workflows_service, _ = services(v1, tool_a)
    configs = {"a": ComponentConfig(step_id="a", new_version_of_id=tool_a.id)}

    v2 = asyncio.run(
        workflows_service.add_version_from_upload(v1, INLINE_PIPELINE.encode(), "wf.cwl", None, configs, OWNER)
    )

    (step,) = v2.steps
    assert step.run_reference == "tool-a.cwl"
    assert "run: tool-a.cwl" in v2.cwl_content
    assert (step.component.name, step.component.version) == ("Tool A", 2)


def test_a_step_versions_its_tool_after_the_lineages_newest_version() -> None:
    # the workflow still runs tool-a v1, but the lineage has moved on to v3 meanwhile
    v1, tool_a, tool_b = uploaded_v1()
    tool_a_v2, tool_a_v3 = tool("tool-a"), tool("tool-a")
    tool_a_v2.version, tool_a_v3.version = 2, 3
    _, workflows_service, _ = services(v1, tool_a, tool_a_v2, tool_a_v3, tool_b)
    configs = {
        "a": ComponentConfig(step_id="a", new_version_of_id=tool_a.id),
        "b": ComponentConfig(step_id="b", reuse_component_id=tool_b.id),
    }

    v2 = asyncio.run(
        workflows_service.add_version_from_upload(v1, upload_zip(a_tool=CHANGED_TOOL), "x.zip", None, configs, OWNER)
    )

    assert v2.steps[0].component.version == 4


LABELLED_TOOL = """
cwlVersion: v1.2
class: CommandLineTool
baseCommand: echo
inputs:
  inp:
    type: File
outputs:
  out:
    type: File
"""


@pytest.mark.parametrize(
    ("sent", "expected"),
    [
        # nothing reviewed - the previous version's hand labels carry over
        ([], {"inp": "CSV"}),
        # reviewed labels add to them, or override them
        ([ManualFormatLabel("out", ParameterDirection.OUTPUT, "GeoTIFF")], {"inp": "CSV", "out": "GeoTIFF"}),
        ([ManualFormatLabel("inp", ParameterDirection.INPUT, "TSV")], {"inp": "TSV"}),
    ],
)
def test_a_step_versioning_a_tool_keeps_its_hand_labels(
    sent: list[ManualFormatLabel], expected: dict[str, str]
) -> None:
    _, workflows_service, repository = services()
    tool_a = asyncio.run(
        workflows_service.tools_service.create_manual(  # type: ignore[attr-defined]
            Component(kind=ComponentKind.TOOL, name="tool-a", cwl_content=LABELLED_TOOL, created_by_id=OWNER),
            format_labels=[ManualFormatLabel("inp", ParameterDirection.INPUT, "CSV")],
        )
    )
    tool_b = tool("tool-b")
    v1 = workflow("wf", tool_a, tool_b, status=ComponentStatus.PUBLISHED)
    v1.workflow.steps[0].step_id, v1.workflow.steps[1].step_id = "a", "b"
    asyncio.run(repository.add_all([v1, tool_b]))
    configs = {
        "a": ComponentConfig(step_id="a", new_version_of_id=tool_a.id, format_labels=sent),
        "b": ComponentConfig(step_id="b", reuse_component_id=tool_b.id),
    }

    v2 = asyncio.run(
        workflows_service.add_version_from_upload(
            v1, upload_zip(a_tool=LABELLED_TOOL.replace("echo", "cat")), "x.zip", None, configs, OWNER
        )
    )

    labels = {p.name: p.format_label for p in v2.steps[0].component.parameters if p.format_label}
    assert labels == expected


def test_a_failing_step_rolls_back_the_tool_version_added_before_it() -> None:
    v1, tool_a, tool_b = uploaded_v1()
    _, workflows_service, _ = services(v1, tool_a, tool_b)
    configs = {
        "a": ComponentConfig(step_id="a", new_version_of_id=tool_a.id),
        # only found while creating b - after tool-a's next version is already added
        "b": ComponentConfig(step_id="b", name="tool-b-new", domains=["other"]),
    }
    broken_b = UPLOAD_TOOL.replace("CommandLineTool", "Operation")

    with pytest.raises(InvalidCwlError):
        asyncio.run(
            workflows_service.add_version_from_upload(
                v1, upload_zip(a_tool=CHANGED_TOOL, b_tool=broken_b), "x.zip", None, configs, OWNER
            )
        )

    assert (workflows_service.uow.commits, workflows_service.uow.rollbacks) == (0, 1)  # type: ignore[attr-defined]


def test_a_step_that_ran_a_workflow_or_nothing_before_cannot_be_versioned() -> None:
    inner = workflow("inner", tool("x"), status=ComponentStatus.PUBLISHED)
    # v1 has only step a - and it ran a nested workflow, not a tool
    v1 = workflow("wf", inner, status=ComponentStatus.PUBLISHED)
    v1.workflow.steps[0].step_id = "a"
    _, workflows_service, _ = services(v1, inner)

    preview = asyncio.run(workflows_service.parse_workflow_upload(upload_zip(), "x.zip", v1, OWNER))

    previous = {p.step_id: p.previous for p in preview.component_previews}
    assert previous["a"] is not None and previous["a"].can_add_version is False
    # b is new in this version - nothing to start from
    assert previous["b"] is None


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
