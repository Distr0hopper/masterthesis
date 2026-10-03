import uuid
from dataclasses import dataclass, field, replace
from typing import Annotated

from fastapi import Depends

from app.application.commands.commands import ComponentCommand, ComponentCommandType
from app.application.exception.component_exceptions import (
    ComponentNameAlreadyExistsError,
    ComponentNotFoundError,
    InvalidCwlError,
    MissingCommandPayloadError,
)
from app.application.exception.workflow_exceptions import (
    ConflictingAuxiliaryFileError,
    ConflictingStepFileError,
    NestedWorkflowsNotReadyError,
    UnpublishableWorkflowComponentsError,
    WorkflowHasUnpublishedComponentsError,
    WorkflowNotReadyToPublishError,
)
from app.application.unit_of_work import UnitOfWork
from app.domain.composite.tree import ConflictingTreeFileError, auxiliary_files, descendants, step_files
from app.domain.models.component import MAX_DESCRIPTION_LENGTH, Component, ComponentKind, ComponentSource, ComponentStatus
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.parameter import Parameter
from app.domain.models.user import User
from app.domain.models.workflow_step import SETTLED_STEP_STATUSES, StepMatchStatus
from app.domain.pagination.pagination import PaginatedList
from app.domain.repository.components_repository import ComponentListFilter
from app.infrastructure.cwl.canvas_graph import canvas_component_ids
from app.infrastructure.cwl.cwl_parser import extract_parameters, extract_schema_url, inject_description
from app.infrastructure.cwl.workflow_generator import assemble_cwl_zip
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.format_service.format_service_client import FormatServiceClient
from app.infrastructure.format_service.ontology import resolve_ontology_url


@dataclass
class ComponentStats:
    tools_published: int
    workflows_published: int
    contributors: int


@dataclass
class ComponentUsage:
    """A workflow version that uses some version(s) of a component lineage."""

    workflow_id: uuid.UUID
    workflow_name: str
    workflow_version: int
    workflow_status: ComponentStatus
    #: the lineage versions its steps are bound to - usually one, ascending
    component_versions: list[int]


@dataclass(frozen=True)
class DraftRef:
    draft_id: uuid.UUID
    name: str


@dataclass
class ComponentDeletionImpact:
    """What deleting one component version would touch - shown before the delete.

    Only what the deleter may see is named: other users' draft workflows and their
    builder drafts are private, so those are just counted."""

    workflows: list[ComponentUsage] = field(default_factory=list)
    hidden_workflow_count: int = 0
    own_drafts: list[DraftRef] = field(default_factory=list)
    other_draft_count: int = 0


@dataclass(frozen=True)
class Download:
    filename: str
    content: bytes | str
    media_type: str


class ComponentsService:
    """Everything that treats a Component uniformly, whatever its kind - the composite's
    shared operations. Kind-specific behaviour lives in ToolsService and WorkflowsService.

    Transactions: the methods a router calls for a write (execute_command, remove) are
    use cases - each opens the unit of work and commits once. Every other writing method
    runs inside its caller's unit and never commits."""

    def __init__(self, uow: UnitOfWork, format_service_client: FormatServiceClient):
        self.uow = uow
        self.format_service_client = format_service_client

    @staticmethod
    def get_service(
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
        format_service_client: Annotated[FormatServiceClient, Depends(FormatServiceClient.get_client)],
    ) -> "ComponentsService":
        return ComponentsService(uow, format_service_client)

    # --- listing -------------------------------------------------------------------------

    async def list_components(
        self, filter: ComponentListFilter, pagination: PaginatedList
    ) -> tuple[list[Component], int]:
        # browse-list callers always see only PUBLISHED components - enforced here rather
        # than trusted from an arbitrary caller-supplied filter, so a public browse request
        # can never leak drafts regardless of what the router builds
        filter = replace(filter, status=ComponentStatus.PUBLISHED, created_by=None)
        return await self.uow.components.find_paginated(filter, pagination)

    async def list_my_components_by_status(
        self,
        created_by_id: uuid.UUID,
        status: ComponentStatus,
        kind: ComponentKind | None,
        pagination: PaginatedList,
    ) -> tuple[list[Component], int]:
        filter = ComponentListFilter(created_by=created_by_id, status=status, kind=kind)
        return await self.uow.components.find_paginated(filter, pagination)

    async def list_all_components(self, filter: ComponentListFilter) -> list[Component]:
        """Every component list_components would page through, unpaged - for callers that
        must order the whole set themselves before paging (the builder palette's ranking)."""
        filter = replace(filter, status=ComponentStatus.PUBLISHED, created_by=None)
        return await self.uow.components.find_all_filtered(filter)

    async def get_latest_components(self, limit: int, kind: ComponentKind | None = None) -> list[Component]:
        components = await self.uow.components.find_all(ComponentStatus.PUBLISHED, kind)
        return sorted(components, key=lambda c: c.created_at, reverse=True)[:limit]

    async def get_stats(self) -> ComponentStats:
        return ComponentStats(
            tools_published=await self.uow.components.count_distinct_names(
                ComponentStatus.PUBLISHED, ComponentKind.TOOL
            ),
            workflows_published=await self.uow.components.count_distinct_names(
                ComponentStatus.PUBLISHED, ComponentKind.WORKFLOW
            ),
            contributors=await self.uow.components.count_distinct_contributors(ComponentStatus.PUBLISHED),
        )

    # --- reading -------------------------------------------------------------------------

    async def get_component(self, component_id: uuid.UUID, kind: ComponentKind | None = None) -> Component:
        """The component with this id - and, when `kind` is given, only if it is that kind:
        a kind-specific endpoint treats the other kind's id as unknown."""
        component = await self.uow.components.find_by_id(component_id)
        if component is None or (kind is not None and component.kind != kind):
            raise ComponentNotFoundError(component_id, kind.value.capitalize() if kind is not None else "Component")
        return component

    async def get_visible_component(
        self, component_id: uuid.UUID, current_user: User | None, kind: ComponentKind | None = None
    ) -> Component:
        component = await self.get_component(component_id, kind)
        if not self.is_visible(component, current_user):
            raise ComponentNotFoundError(component_id, kind.value.capitalize() if kind is not None else "Component")
        return component

    @staticmethod
    def is_visible(component: Component, current_user: User | None) -> bool:
        if component.status == ComponentStatus.PUBLISHED:
            return True
        return current_user is not None and component.created_by_id == current_user.id

    async def get_versions(self, component: Component) -> list[Component]:
        return await self.uow.components.find_versions_by_name(component.name)

    async def get_visible_versions(self, component: Component, current_user: User | None) -> list[Component]:
        versions = await self.get_versions(component)
        return [v for v in versions if self.is_visible(v, current_user)]

    async def load_tree(self, component: Component) -> Component:
        """`component` with its whole composite below it loaded - see ComponentsRepository.load_tree."""
        return await self.uow.components.load_tree(component)

    # --- names ---------------------------------------------------------------------------

    async def find_latest_version_by_name(self, name: str, exclude_id: uuid.UUID | None = None) -> Component | None:
        """The newest version of the lineage holding this exact name, if it exists.

        `exclude_id` leaves out the lineage that version belongs to - a component trivially
        holds its own name, so a rename check has to skip it or it would always collide.
        """
        latest = await self.uow.components.find_latest_by_name(name)
        if latest is None or exclude_id is None:
            return latest
        excluded = await self.uow.components.find_by_id(exclude_id)
        return None if excluded is not None and excluded.name == latest.name else latest

    async def find_visible_latest_version_by_name(
        self, name: str, current_user: User | None, exclude_id: uuid.UUID | None = None
    ) -> Component | None:
        """The newest version of this lineage, but only if the caller may see it.

        A name can be held by someone else's unpublished draft. The name is still taken -
        it is a global key across both kinds (favourites reference components by name, and
        uq_components_name_version pins one row per name+version) - but the caller has no
        business learning anything about a draft that is not theirs, and linking them to a
        component they cannot open is a dead end.
        """
        existing = await self.find_latest_version_by_name(name, exclude_id)
        if existing is None or not self.is_visible(existing, current_user):
            return None
        return existing

    async def require_name_available(
        self, name: str, hint: str = "choose a different name", exclude_id: uuid.UUID | None = None
    ) -> None:
        """Enforces the lineage-name uniqueness in the service, so a collision comes back as
        a clean 409 rather than an IntegrityError from the database."""
        if await self.find_latest_version_by_name(name, exclude_id) is not None:
            raise ComponentNameAlreadyExistsError(name, hint)

    # --- ports ---------------------------------------------------------------------------

    @staticmethod
    def parse_ports(cwl_content: str, context: str, source: ComponentSource) -> list[Parameter]:
        """The ports of any CWL document - a tool's inputs/outputs, or a workflow's."""
        try:
            parameters = extract_parameters(cwl_content)
        except ValueError as err:
            raise InvalidCwlError(context, str(err)) from err

        # the packager writes formats it cannot vouch for - only a human-authored document's
        # formats are trusted
        if source == ComponentSource.AUTOMATED_PACKAGING:
            for parameter in parameters:
                parameter.format = None
        return parameters

    @staticmethod
    def ontology_url_for(cwl_content: str) -> str | None:
        """The ontology a document's formats belong to - see Component.ontology_url."""
        return resolve_ontology_url(extract_schema_url(cwl_content))

    async def resolve_format_labels(self, ontology_url: str | None, parameters: list[Parameter]) -> None:
        """Fills format_label in place - shared by create and the parse previews, so what
        the user reviews is what gets saved."""
        # a format identifier only has a label within an ontology - without one (no
        # $schemas in the CWL) there is nothing to resolve against
        formats = {p.format for p in parameters if p.format}
        if ontology_url is None or not formats:
            return
        labels = await self.format_service_client.resolve_labels(formats, ontology_url)
        for parameter in parameters:
            if parameter.format:
                parameter.format_label = labels.get(parameter.format)

    async def assign_ports(self, component: Component, context: str) -> None:
        """Parse `component`'s ports and ontology from its CWL and resolve their format labels."""
        component.parameters = self.parse_ports(component.cwl_content, context, component.source)
        component.ontology_url = self.ontology_url_for(component.cwl_content)
        await self.resolve_format_labels(component.ontology_url, component.parameters)

    @staticmethod
    def truncate_description(description: str | None) -> str | None:
        # explicit user-submitted descriptions are already length-validated at the DTO
        # boundary (a no-op here) - this only actually kicks in for descriptions pulled
        # from the CWL's own `doc:` field or a repo's README during packaging, neither of
        # which the user directly typed, so silently truncating beats a hard failure
        return description if description is None else description[:MAX_DESCRIPTION_LENGTH]

    # --- lifecycle -----------------------------------------------------------------------

    async def _publish(
        self, component: Component, current_user_id: uuid.UUID, publish_components: bool = False
    ) -> Component:
        """Make a component public.

        A tool simply flips. A workflow takes its whole tree into account: a public
        workflow whose steps run draft components would be broken for every other user -
        drafts are owner-only - so every component below it must be published too, at any
        depth. `publish_components` opts into publishing them as part of this action;
        without it the draft components are reported and nothing is changed.
        """
        if component.status == ComponentStatus.PUBLISHED:
            return component
        if component.is_tool:
            component.status = ComponentStatus.PUBLISHED
            return await self.uow.components.add(component)

        await self.load_tree(component)
        if not self._is_settled(component):
            raise WorkflowNotReadyToPublishError(component.id)
        unsettled = sorted({c.name for c in descendants(component) if c.is_workflow and not self._is_settled(c)})
        if unsettled:
            raise NestedWorkflowsNotReadyError(unsettled)

        drafts = [c for c in descendants(component) if c.status == ComponentStatus.DRAFT]
        if drafts:
            foreign = sorted({c.name for c in drafts if c.created_by_id != current_user_id})
            if foreign:
                raise UnpublishableWorkflowComponentsError(foreign)
            if not publish_components:
                raise WorkflowHasUnpublishedComponentsError(sorted({c.name for c in drafts}))

        for c in [*drafts, component]:
            c.status = ComponentStatus.PUBLISHED
        await self.uow.components.add_all([*drafts, component])
        return component

    @staticmethod
    def _is_settled(workflow: Component) -> bool:
        return all(step.match_status in SETTLED_STEP_STATUSES for step in workflow.steps)

    async def _unpublish(self, component: Component) -> Component:
        """Inverse of publish - only the creator can see the component again. Idempotent."""
        if component.status == ComponentStatus.DRAFT:
            return component
        component.status = ComponentStatus.DRAFT
        return await self.uow.components.add(component)

    async def _update_description(self, component: Component, description: str | None) -> Component:
        component.description = description
        return await self.uow.components.add(component)

    async def _update_domains(self, component: Component, domains: list[str] | None) -> Component:
        if not domains:
            raise MissingCommandPayloadError(ComponentCommandType.UPDATE_DOMAIN, "domains")
        component.domains = [ComponentDomain(domain=d) for d in domains]
        return await self.uow.components.add(component)

    async def execute_command(
        self, component: Component, command: ComponentCommand, current_user_id: uuid.UUID
    ) -> Component:
        async with self.uow:
            match command.type:
                case ComponentCommandType.ADD_FAVORITE:
                    # favoriting is scoped to the whole lineage (name), not the specific
                    # version row the star was clicked on - so every version favorites together
                    await self.uow.favorites.add(current_user_id, component.name)
                case ComponentCommandType.REMOVE_FAVORITE:
                    await self.uow.favorites.remove(current_user_id, component.name)
                case ComponentCommandType.PUBLISH:
                    component = await self._publish(component, current_user_id, command.publish_components)
                case ComponentCommandType.UNPUBLISH:
                    component = await self._unpublish(component)
                case ComponentCommandType.UPDATE_DESCRIPTION:
                    component = await self._update_description(component, command.description)
                case ComponentCommandType.UPDATE_DOMAIN:
                    component = await self._update_domains(component, command.domains)
            await self.uow.commit()
        return await self.reload(component)

    async def reload(self, component: Component) -> Component:
        """`component` freshly read with one composite level loaded - for the response after
        a write, see ComponentsRepository.find_by_id_fresh."""
        reloaded = await self.uow.components.find_by_id_fresh(component.id)
        assert reloaded is not None
        return reloaded

    # --- favorites -----------------------------------------------------------------------

    async def favorited_names(self, user: User | None) -> set[str]:
        return await self.uow.favorites.find_favorited_names(user.id) if user is not None else set()

    # --- usages and deletion -------------------------------------------------------------

    async def list_usages(self, component: Component, current_user: User | None) -> list[ComponentUsage]:
        """The workflows whose steps run any version of `component`'s lineage - its parents in
        the composite, for the detail page's "Used in these workflows". Same visibility as
        get_visible_component: published workflows, plus the user's own drafts."""
        rows = await self.uow.workflows.find_usages_of_lineage(
            component.name, current_user.id if current_user is not None else None
        )
        usages: dict[uuid.UUID, ComponentUsage] = {}
        for row in rows:  # ordered by workflow name and version, then child version
            usage = usages.get(row.workflow_id)
            if usage is None:
                usages[row.workflow_id] = ComponentUsage(
                    workflow_id=row.workflow_id,
                    workflow_name=row.workflow_name,
                    workflow_version=row.workflow_version,
                    workflow_status=row.workflow_status,
                    component_versions=[row.component_version],
                )
            else:
                usage.component_versions.append(row.component_version)
        return list(usages.values())

    async def get_deletion_impact(self, component: Component, current_user: User) -> ComponentDeletionImpact:
        """The workflows and builder drafts that reference exactly this component version."""
        impact = ComponentDeletionImpact()

        parents: dict[uuid.UUID, Component] = {}
        for step in await self.uow.workflows.find_steps_by_component_id(component.id):
            if step.parent is not None:
                parents[step.parent.id] = step.parent
        for parent in sorted(parents.values(), key=lambda w: (w.name, w.version)):
            if self.is_visible(parent, current_user):
                impact.workflows.append(
                    ComponentUsage(
                        workflow_id=parent.id,
                        workflow_name=parent.name,
                        workflow_version=parent.version,
                        workflow_status=parent.status,
                        component_versions=[component.version],
                    )
                )
            else:
                impact.hidden_workflow_count += 1

        component_id = str(component.id)
        for draft in await self.uow.drafts.find_all_mentioning(component_id):
            if component_id not in canvas_component_ids(draft.canvas_state):
                continue
            if draft.created_by_id == current_user.id:
                impact.own_drafts.append(DraftRef(draft_id=draft.id, name=draft.name))
            else:
                impact.other_draft_count += 1
        impact.own_drafts.sort(key=lambda d: d.name)
        return impact

    async def _detach(self, component_id: uuid.UUID) -> None:
        """Unmatch every step pinned to a component version that is about to be deleted -
        a tool or a nested workflow alike.

        The FK's ON DELETE SET NULL alone would leave such steps CONFIRMED/SUGGESTED with
        no component, and their workflow public. Deliberately never rebinds to another
        version of the lineage - the user picks the replacement. Builder drafts need no
        cascade: their canvas is checked for missing components whenever it is opened.
        """
        steps = await self.uow.workflows.find_steps_by_component_id(component_id)
        if not steps:
            return
        reverted: dict[uuid.UUID, Component] = {}
        for step in steps:
            step.component_id = None
            step.component = None
            step.match_status = StepMatchStatus.UNMATCHED
            step.match_score = None
            # a public workflow with an unmatched step would be broken for everyone
            parent = step.parent
            if parent is not None and parent.status == ComponentStatus.PUBLISHED:
                parent.status = ComponentStatus.DRAFT
                reverted[parent.id] = parent
        await self.uow.workflows.add_steps(steps, list(reverted.values()))

    async def remove(
        self, component: Component, deleted_by_id: uuid.UUID, delete_linked_draft: bool = False
    ) -> bool:
        """Delete one component version, cascading into everything that references it.

        The steps pinned to it are unmatched first (see _detach), and the lineage's favorites
        go with its last version. For a workflow, `delete_linked_draft` also deletes the
        builder canvas it was synced from - the mirror of WorkflowDraftService.delete_draft's
        delete_linked_workflow: both directions of the draft <-> workflow link are opt-in,
        so neither side's delete silently destroys the other. Returns whether a draft was
        deleted.

        All of it is one transaction: either the component and everything cascading from it
        is gone, or nothing is.
        """
        async with self.uow:
            deleted_draft = await self._remove(component, deleted_by_id, delete_linked_draft)
            await self.uow.commit()
        return deleted_draft

    async def _remove(self, component: Component, deleted_by_id: uuid.UUID, delete_linked_draft: bool = False) -> bool:
        versions = await self.get_versions(component)
        # read before the row goes away - the FK is ON DELETE SET NULL on the workflow side,
        # so nothing else recovers which draft this came from
        draft_id = component.workflow.draft_id if component.workflow is not None else None
        name = component.name

        await self._detach(component.id)
        await self.uow.components.delete(component)
        if len(versions) == 1:
            await self.uow.favorites.delete_by_name(name)

        if not delete_linked_draft or draft_id is None:
            return False
        draft = await self.uow.drafts.find_by_id(draft_id)
        if draft is None or draft.created_by_id != deleted_by_id:
            return False
        await self.uow.drafts.delete(draft)
        return True

    async def remove_synced_from_draft(self, draft_id: uuid.UUID, owner_id: uuid.UUID) -> int:
        """Delete every workflow version synced from this builder draft that the user owns.
        Returns how many were removed. Runs inside the caller's unit of work."""
        removed = 0
        for workflow in await self.uow.workflows.find_all_synced_from_draft(draft_id):
            if workflow.created_by_id == owner_id:
                await self._remove(workflow, owner_id)
                removed += 1
        return removed

    # --- download ------------------------------------------------------------------------

    async def get_download(self, component: Component) -> Download:
        """A tool downloads as its .cwl document; a workflow as a zip of its pipeline plus
        every step document of its tree - nested workflows and their tools included - and
        every file any of them imports."""
        if component.is_tool:
            return Download(
                filename=f"{component.name}-v{component.version}.cwl",
                content=inject_description(component.cwl_content, component.description),
                media_type="application/yaml",
            )

        await self.load_tree(component)
        # same archive layout and naming as the builder's "Export CWL" (assemble_cwl_zip).
        # Step files keep their stored run_reference - that is what each pipeline's `run:`
        # lines point at, so they cannot be renamed here.
        try:
            files = step_files(component)
        except ConflictingTreeFileError as err:
            raise ConflictingStepFileError(err.path) from err
        try:
            extras = auxiliary_files(component)
        except ConflictingTreeFileError as err:
            raise ConflictingAuxiliaryFileError(err.path) from err
        filename, content = assemble_cwl_zip(component.name, component.cwl_content, files, extras)
        return Download(filename=filename, content=content, media_type="application/zip")
