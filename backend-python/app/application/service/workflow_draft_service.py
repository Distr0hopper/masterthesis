import json
import logging
import uuid
from typing import Annotated, Any

from fastapi import Depends

from app.application.exception.workflow_draft_exceptions import (
    ExportValidationError,
    WorkflowDraftForbiddenError,
    WorkflowDraftNotFoundError,
)
from app.domain.models.component import Component
from app.domain.models.parameter import ParameterDirection
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_draft import WorkflowDraft
from app.domain.repository.components_repository import ComponentsRepository
from app.application.service.workflows_service import WorkflowsService
from app.domain.repository.workflow_draft_repository import WorkflowDraftRepository
from app.infrastructure.cwl.canvas_graph import CanvasCycleError, topological_sort
from app.infrastructure.cwl.workflow_generator import (
    PortSpec,
    assemble_cwl_zip,
    build_workflow_document,
    cwl_filename_for,
    generate_workflow_inputs_yaml,
    render_workflow_cwl,
    safe_workflow_slug,
)

logger = logging.getLogger("app.application.service.workflow_draft_service")


def _is_file_type(cwl_type: str) -> bool:
    return cwl_type.strip().lower().startswith("file")


class WorkflowDraftService:
    def __init__(
        self,
        repository: WorkflowDraftRepository,
        components_repository: ComponentsRepository,
        workflows_service: WorkflowsService,
    ):
        self.repository = repository
        self.components_repository = components_repository
        self.workflows_service = workflows_service

    @staticmethod
    def get_service(
        repository: Annotated[WorkflowDraftRepository, Depends(WorkflowDraftRepository.get_repository)],
        components_repository: Annotated[ComponentsRepository, Depends(ComponentsRepository.get_repository)],
        workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    ) -> "WorkflowDraftService":
        return WorkflowDraftService(repository, components_repository, workflows_service)

    async def list_my_drafts(self, user_id: uuid.UUID) -> list[WorkflowDraft]:
        return await self.repository.find_all_by_user(user_id)

    async def linked_workflow_ids(self, draft_ids: set[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
        """{draft_id: workflow_id} for the drafts synced to a My Workflows entry."""
        return await self.workflows_service.linked_workflow_ids(draft_ids)

    async def get_draft(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> WorkflowDraft:
        """Fetch one draft, enforcing ownership. Every mutating path goes through this."""
        draft = await self.repository.find_by_id(draft_id)
        if draft is None:
            raise WorkflowDraftNotFoundError(draft_id)
        if draft.created_by_id != user_id:
            raise WorkflowDraftForbiddenError()
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
        return await self.repository.save(draft)

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
        return await self.repository.save(draft)

    async def delete_draft(
        self, draft: WorkflowDraft, user_id: uuid.UUID, delete_linked_workflow: bool = False
    ) -> None:
        # by default the FK is ON DELETE SET NULL, so the synced My Workflows copy just
        # loses its "edit in builder" link and stays. The user can opt to drop it too.
        if delete_linked_workflow:
            await self.workflows_service.delete_by_draft_id(draft.id, user_id)
        await self.repository.delete(draft)

    async def _fetch_components(self, component_ids: list[str]) -> dict[str, Component]:
        """{component_id: Component} for every id on the canvas.

        Raises ExportValidationError naming the ids that no longer resolve - a component
        deleted since the draft was saved must fail loudly, not export a broken archive.
        """
        components: dict[str, Component] = {}
        missing: list[str] = []

        for raw_id in dict.fromkeys(component_ids):
            try:
                component_id = uuid.UUID(raw_id)
            except (ValueError, AttributeError, TypeError):
                missing.append(str(raw_id))
                continue
            component = await self.components_repository.find_by_id(component_id)
            if component is None:
                missing.append(str(raw_id))
            else:
                components[raw_id] = component

        if missing:
            raise ExportValidationError(
                f"{len(missing)} component(s) on the canvas no longer exist in the repository"
            )
        return components

    @staticmethod
    def _to_port_spec(component: Component) -> PortSpec:
        spec = PortSpec(name=component.name)
        for parameter in component.parameters:
            if parameter.direction == ParameterDirection.OUTPUT:
                if _is_file_type(parameter.cwl_type):
                    spec.file_outputs[parameter.name] = parameter.cwl_type
            elif _is_file_type(parameter.cwl_type):
                spec.file_inputs[parameter.name] = parameter.cwl_type
            else:
                spec.config_inputs[parameter.name] = parameter.cwl_type
        return spec

    async def export_to_zip(self, draft: WorkflowDraft) -> tuple[str, bytes]:
        """Generate the main Workflow CWL plus one file per step, zipped.

        Returns (filename, zip_bytes). Raises ExportValidationError for anything that
        makes the canvas unexportable.
        """
        workflow_doc, components, ports = await self._build_workflow_document(draft)
        step_files = [
            (cwl_filename_for(spec.name), components[cid].cwl_content) for cid, spec in ports.items()
        ]
        filename, zip_bytes = assemble_cwl_zip(draft.name, render_workflow_cwl(workflow_doc), step_files)
        logger.info(f"Generated archive for draft {draft.id}: {len(step_files)} step file(s)")
        return filename, zip_bytes

    async def export_inputs_yaml(self, draft: WorkflowDraft) -> tuple[str, str]:
        """The job file for the exported workflow - one placeholder per workflow input.

        Returns (filename, yaml). Built from the same document as export_to_zip, so it
        always matches the .cwl that export produces.
        """
        workflow_doc, _components, _ports = await self._build_workflow_document(draft)
        return f"{safe_workflow_slug(draft.name)}-inputs.yaml", generate_workflow_inputs_yaml(draft.name, workflow_doc)

    async def _build_workflow_document(
        self, draft: WorkflowDraft
    ) -> tuple[dict[str, Any], dict[str, Component], dict[str, PortSpec]]:
        """The draft's canvas as a Workflow document, plus the components and port specs it
        was built from. Raises ExportValidationError for anything that makes it unexportable."""
        try:
            canvas = json.loads(draft.canvas_state)
        except json.JSONDecodeError as err:
            raise ExportValidationError("The saved canvas could not be read") from err

        nodes = canvas.get("nodes") or []
        edges = canvas.get("edges") or []
        if not nodes:
            raise ExportValidationError("Canvas is empty")

        component_ids = [n.get("data", {}).get("componentId") for n in nodes]
        if not all(component_ids):
            raise ExportValidationError("One or more nodes have no linked component")

        components = await self._fetch_components(component_ids)
        ports = {cid: self._to_port_spec(component) for cid, component in components.items()}

        try:
            ordered_nodes = topological_sort(nodes, edges)
        except CanvasCycleError as err:
            raise ExportValidationError(str(err)) from err

        workflow_doc = build_workflow_document(
            workflow_name=draft.name, ordered_nodes=ordered_nodes, edges=edges, ports=ports
        )
        return workflow_doc, components, ports

    async def sync_to_my_workflows(self, draft: WorkflowDraft, user_id: uuid.UUID) -> Workflow:
        """Mirror the draft's generated archive into the user's My Workflows list.

        Not the same as making a workflow public - that stays a separate, explicit action
        on the My Workflows page (WorkflowsService.publish). This only materialises the
        canvas as a PENDING_VALIDATION Workflow row.

        Deliberately separate from export: downloading a file should not create rows.
        Idempotent per draft - the Builder calls this on every Save, so the first call
        creates the Workflow and later ones re-sync it in place (see
        WorkflowsService.upsert_from_draft) rather than piling up near-duplicates.
        """
        _filename, zip_bytes = await self.export_to_zip(draft)

        workflow = await self.workflows_service.upsert_from_draft(
            zip_bytes=zip_bytes,
            name=draft.name,
            # the link the UI follows back into the builder, and the key this upsert is on
            draft_id=draft.id,
            created_by_id=user_id,
        )
        logger.info(f"Synced draft {draft.id} into My Workflows as workflow {workflow.id}")
        return workflow
