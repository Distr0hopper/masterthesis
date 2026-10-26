import logging
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends

from app.application.exception.workflow_draft_exceptions import (
    ExportValidationError,
    WorkflowDraftNotFoundError,
)
from app.application.service.components_service import ComponentsService
from app.application.service.workflows_service import StepBinding, WorkflowsService
from app.application.unit_of_work import UnitOfWork
from app.domain.composite import lifecycle
from app.domain.composite.tree import ArchiveLayout, ConflictingTreeFileError
from app.domain.models.component import Component
from app.domain.models.parameter import ParameterDirection
from app.domain.models.workflow_draft import WorkflowDraft
from app.infrastructure.cwl.canvas_graph import (
    CanvasCycleError,
    CanvasFormatError,
    canvas_component_ids,
    node_component_id,
    parse_canvas,
    topological_sort,
)
from app.infrastructure.cwl.cwl_parser import extract_input_declarations
from app.infrastructure.cwl.workflow_generator import (
    PortSpec,
    assemble_cwl_zip,
    assign_step_ids,
    build_workflow_document,
    cwl_filename_for,
    generate_workflow_inputs_yaml,
    render_workflow_cwl,
    safe_workflow_slug,
)
from app.infrastructure.db.unit_of_work import SqlUnitOfWork

logger = logging.getLogger("app.application.service.workflow_draft_service")


def _is_file_type(cwl_type: str) -> bool:
    return cwl_type.strip().lower().startswith("file")


@dataclass(frozen=True)
class _GeneratedWorkflow:
    """A canvas turned into a Workflow document, with what it was built from - export
    and sync each need a different part of it, so the canvas is parsed only once."""

    document: dict[str, Any]
    #: in topological order - the order the steps are numbered and stored in
    ordered_nodes: list[dict[str, Any]]
    components: dict[str, Component]
    ports: dict[str, PortSpec]


class WorkflowDraftService:
    def __init__(
        self,
        uow: UnitOfWork,
        components_service: ComponentsService,
        workflows_service: WorkflowsService,
    ):
        self.uow = uow
        self.components_service = components_service
        self.workflows_service = workflows_service

    @staticmethod
    def get_service(
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
        components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
        workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    ) -> "WorkflowDraftService":
        return WorkflowDraftService(uow, components_service, workflows_service)

    async def list_my_drafts(self, user_id: uuid.UUID) -> list[WorkflowDraft]:
        return await self.uow.drafts.find_all_by_user(user_id)

    async def linked_workflows(self, draft_ids: set[uuid.UUID]) -> dict[uuid.UUID, Component]:
        """{draft_id: newest workflow version} for the drafts synced to a My Components entry."""
        return await self.workflows_service.linked_workflows(draft_ids)

    async def locked_names(self, workflows: Iterable[Component]) -> set[str]:
        """The lineages among `workflows` whose name is fixed - see lifecycle.name_locked: a
        version of them is public, so the builder must not offer to rename the canvas."""
        names = sorted({w.name for w in workflows})
        return await self.uow.components.find_names_with_status(names, lifecycle.PUBLIC_STATUSES)

    async def get_draft(self, draft_id: uuid.UUID) -> WorkflowDraft:
        """Fetch one draft - who may open it is the router's check (WorkflowDraftPermissionValidator)."""
        draft = await self.uow.drafts.find_by_id(draft_id)
        if draft is None:
            raise WorkflowDraftNotFoundError(draft_id)
        return draft

    async def create_draft(
        self,
        name: str,
        canvas_state: str,
        node_count: int,
        user_id: uuid.UUID,
    ) -> WorkflowDraft:
        draft = WorkflowDraft(
            name=name,
            canvas_state=canvas_state,
            node_count=node_count,
            created_by_id=user_id,
        )
        async with self.uow:
            await self.uow.drafts.add(draft)
            await self.uow.commit()
        return draft

    async def update_draft(
        self,
        draft: WorkflowDraft,
        name: str,
        canvas_state: str,
        node_count: int,
    ) -> WorkflowDraft:
        # full replacement, not a patch - the editor always sends its complete canvas
        draft.name = name
        draft.canvas_state = canvas_state
        draft.node_count = node_count
        async with self.uow:
            await self.uow.drafts.add(draft)
            await self.uow.commit()
        return draft

    async def delete_draft(self, draft: WorkflowDraft, delete_linked_workflow: bool = False) -> None:
        # by default the FK is ON DELETE SET NULL, so the synced My Components copy just
        # loses its "edit in builder" link and stays. The user can opt to drop it too -
        # every version synced from this canvas. One transaction either way.
        async with self.uow:
            if delete_linked_workflow:
                await self.components_service.remove_synced_from_draft(draft.id, draft.created_by_id)
            await self.uow.drafts.delete(draft)
            await self.uow.commit()

    async def missing_component_ids(self, draft: WorkflowDraft) -> list[str]:
        """The componentIds on the draft's canvas that no longer resolve - lets the builder
        flag deleted components as soon as a draft is opened, not only on export."""
        _found, missing = await self._resolve_components(draft, canvas_component_ids(draft.canvas_state))
        return missing

    async def _resolve_components(
        self, draft: WorkflowDraft, component_ids: list[str]
    ) -> tuple[dict[str, Component], list[str]]:
        """({component_id: Component}, [unresolvable ids]) for the ids on a canvas.

        Only what the canvas's owner may read resolves - a canvas is client-written JSON, so
        an id of someone else's draft on it must not export that draft's CWL or bind a step
        to it. Such an id is missing like a deleted one (the readability rule of
        registry.is_readable_by, compared by id: the draft's creator may not be loaded)."""
        components: dict[str, Component] = {}
        missing: list[str] = []

        for raw_id in dict.fromkeys(component_ids):
            try:
                component_id = uuid.UUID(raw_id)
            except (ValueError, AttributeError, TypeError):
                missing.append(str(raw_id))
                continue
            component = await self.uow.components.find_by_id(component_id)
            readable = component is not None and (
                lifecycle.is_public(component) or component.created_by_id == draft.created_by_id
            )
            if not readable:
                missing.append(str(raw_id))
            else:
                components[raw_id] = component
        return components, missing

    async def _fetch_components(self, draft: WorkflowDraft, component_ids: list[str]) -> dict[str, Component]:
        """{component_id: Component} for every id on the canvas.

        Raises ExportValidationError naming the ids that no longer resolve - a component
        deleted since the draft was saved must fail loudly, not export a broken archive.
        """
        components, missing = await self._resolve_components(draft, component_ids)
        if missing:
            raise ExportValidationError(f"{len(missing)} component(s) on the canvas no longer exist in the repository")
        return components

    @staticmethod
    def _to_port_spec(component: Component) -> PortSpec:
        # uniform over the composite: a nested workflow exposes its ports exactly like a tool
        spec = PortSpec(name=component.name)
        declarations = extract_input_declarations(component.cwl_content)
        for parameter in component.parameters:
            if parameter.direction == ParameterDirection.OUTPUT:
                if _is_file_type(parameter.cwl_type):
                    spec.file_outputs[parameter.name] = parameter.cwl_type
            elif _is_file_type(parameter.cwl_type):
                spec.file_inputs[parameter.name] = parameter.cwl_type
            else:
                spec.config_inputs[parameter.name] = parameter.cwl_type
                if parameter.name in declarations:
                    declared_type, default = declarations[parameter.name]
                    spec.config_types[parameter.name] = declared_type
                    if default is not None:
                        spec.config_defaults[parameter.name] = default
        return spec

    async def export_to_zip(self, draft: WorkflowDraft) -> tuple[str, bytes]:
        """Generate the main Workflow CWL plus one file per step, zipped.

        A node running a workflow brings its whole tree along - the nested pipeline, the
        step documents below it and anything they import - in a folder of its own, where
        its `run:` lines resolve (see ArchiveLayout).

        Returns (filename, zip_bytes). Raises ExportValidationError for anything that
        makes the canvas unexportable.
        """
        generated = await self._build_workflow_document(draft)
        step_ids = assign_step_ids(generated.ordered_nodes, generated.ports)
        # the archive's copy of the document: a node running a workflow points into its folder
        steps = {step_id: dict(step) for step_id, step in generated.document["steps"].items()}
        layout = ArchiveLayout()
        try:
            for node in generated.ordered_nodes:
                cid = node_component_id(node)
                step = steps[step_ids[node["id"]]]
                step["run"] = layout.place(generated.components[cid], step["run"], "")
        except ConflictingTreeFileError as err:
            raise ExportValidationError(
                f"Two different documents on the canvas need the file name '{err.path}' - rename one of them"
            ) from err
        files = self.components_service.laid_out_documents(layout)
        filename, zip_bytes = assemble_cwl_zip(
            draft.name,
            render_workflow_cwl({**generated.document, "steps": steps}),
            files,
            sorted(layout.imported.items()),
        )
        logger.info(f"Generated archive for draft {draft.id}: {len(files)} step file(s)")
        return filename, zip_bytes

    async def export_inputs_yaml(self, draft: WorkflowDraft) -> tuple[str, str]:
        """The job file for the exported workflow - one placeholder per workflow input.

        Returns (filename, yaml). Built from the same document as export_to_zip, so it
        always matches the .cwl that export produces.
        """
        generated = await self._build_workflow_document(draft)
        return (
            f"{safe_workflow_slug(draft.name)}-inputs.yaml",
            generate_workflow_inputs_yaml(draft.name, generated.document),
        )

    async def _build_workflow_document(self, draft: WorkflowDraft) -> _GeneratedWorkflow:
        """The draft's canvas as a Workflow document, plus what it was built from. Raises
        ExportValidationError for anything that makes it unexportable."""
        try:
            nodes, edges = parse_canvas(draft.canvas_state)
        except CanvasFormatError as err:
            raise ExportValidationError(str(err)) from err
        if not nodes:
            raise ExportValidationError("Canvas is empty")

        component_ids = [node_component_id(n) for n in nodes]
        if not all(component_ids):
            raise ExportValidationError("One or more nodes have no linked component")

        components = await self._fetch_components(draft, [cid for cid in component_ids if cid is not None])
        for component in components.values():
            await self.components_service.load_tree(component)
        ports = {cid: self._to_port_spec(component) for cid, component in components.items()}

        try:
            ordered_nodes = topological_sort(nodes, edges)
        except CanvasCycleError as err:
            raise ExportValidationError(str(err)) from err

        document = build_workflow_document(
            workflow_name=draft.name,
            ordered_nodes=ordered_nodes,
            edges=edges,
            ports=ports,
            has_subworkflows=any(c.is_workflow for c in components.values()),
        )
        return _GeneratedWorkflow(document, ordered_nodes, components, ports)

    async def sync_to_my_components(self, draft: WorkflowDraft) -> Component:
        """Mirror the draft's generated archive into the user's My Components list.

        Not the same as making a workflow public - that stays a separate, explicit action
        on its My Components page (WorkflowsService.publish). This only materialises the
        canvas as a DRAFT workflow.

        Deliberately separate from export: downloading a file should not create rows.
        Idempotent per draft - the Builder calls this on every Save, so the first call
        creates the workflow and later ones re-sync it (see
        WorkflowsService.upsert_from_draft) rather than piling up near-duplicates.

        Each step is bound to exactly the component its node was dropped from - the canvas
        already knows, so nothing is matched by file name.
        """
        generated = await self._build_workflow_document(draft)
        step_ids = assign_step_ids(generated.ordered_nodes, generated.ports)
        bindings = [
            StepBinding(
                step_id=step_ids[node["id"]],
                run_reference=cwl_filename_for(generated.ports[node_component_id(node)].name),
                component_id=uuid.UUID(node_component_id(node)),
            )
            for node in generated.ordered_nodes
        ]

        async with self.uow:
            workflow = await self.workflows_service.upsert_from_draft(
                pipeline_content=render_workflow_cwl(generated.document),
                bindings=bindings,
                name=draft.name,
                # the link the UI follows back into the builder, and the key this upsert is on
                draft_id=draft.id,
                # the canvas's owner - drafts are owner-only, so that is who saved it
                created_by_id=draft.created_by_id,
            )
            await self.uow.commit()
        workflow = await self.components_service.reload(workflow)
        logger.info(f"Synced draft {draft.id} into My Components as workflow {workflow.id}")
        return workflow
