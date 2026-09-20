import uuid
import zipfile
from dataclasses import dataclass, replace
from io import BytesIO
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from app.application.commands.commands import WorkflowCommand, WorkflowCommandType, WorkflowStepCommand, WorkflowStepCommandType
from app.application.exception.component_exceptions import ComponentNotFoundError
from app.application.exception.workflow_exceptions import (
    ComponentDomainRequiredError,
    DuplicateExtractedComponentNameError,
    ExtractedComponentNameCollisionError,
    InvalidExtractedComponentNameError,
    InvalidWorkflowArchiveError,
    InvalidWorkflowCwlError,
    UnsupportedInlineWorkflowStepError,
    WorkflowNotFoundError,
    WorkflowNotReadyToPublishError,
    WorkflowStepNotFoundError,
    WorkflowStepNotMatchedError,
)
from app.application.service.components_service import ComponentsService
from app.domain.models.component import Component, ComponentSource
from app.domain.models.user import User
from app.domain.models.workflow import Workflow, WorkflowSource, WorkflowStatus
from app.domain.models.workflow_domain import WorkflowDomain
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep
from app.domain.pagination.pagination import PaginatedList
from app.domain.repository.components_repository import ComponentsRepository
from app.domain.repository.workflows_repository import WorkflowListFilter, WorkflowsRepository
from app.infrastructure.cwl.cwl_matcher import best_match
from app.infrastructure.cwl.cwl_parser import inject_cwl_version
from app.infrastructure.cwl.workflow_generator import assemble_cwl_zip, cwl_filename_for
from app.infrastructure.cwl.workflow_parser import (
    ExtractedComponent,
    externalize_inline_steps,
    extract_inline_components,
    extract_step_definitions,
    extract_workflow_steps,
    find_workflow_file,
    is_self_contained,
    read_workflow_overview,
    strip_cwl_extension,
)


@dataclass
class WorkflowUploadPreview:
    """Everything WorkflowsService.parse_workflow_upload reports back about one upload,
    which may be a bare .cwl file or a .zip archive - is_zip/missing_external_refs only
    apply to the zip case, [] otherwise."""

    is_zip: bool
    is_self_contained: bool
    workflow_name: str | None
    step_count: int
    extracted_components: list[ExtractedComponent]
    external_refs: list[str]
    unsupported_inline_steps: list[str]
    missing_external_refs: list[str]


@dataclass
class WorkflowUploadContent:
    """The zip-vs-bare-file dispatch result shared by parse_workflow_upload and
    create_from_upload - available_files is None for a bare .cwl upload (nothing to
    cross-check external refs against)."""

    is_zip: bool
    cwl_content: str
    pipeline_filename: str | None
    available_files: set[str] | None


if TYPE_CHECKING:
    # deferred import - favorites_service.py imports WorkflowsService, so importing
    # FavoritesService here at module load time would create a circular import
    from app.application.service.favorites_service import FavoritesService


class WorkflowsService:
    def __init__(
        self,
        workflows_repository: WorkflowsRepository,
        components_repository: ComponentsRepository,
        components_service: ComponentsService,
    ):
        self.workflows_repository = workflows_repository
        self.components_repository = components_repository
        self.components_service = components_service

    @staticmethod
    def get_service(
        workflows_repository: Annotated[WorkflowsRepository, Depends(WorkflowsRepository.get_repository)],
        components_repository: Annotated[ComponentsRepository, Depends(ComponentsRepository.get_repository)],
        components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    ) -> "WorkflowsService":
        return WorkflowsService(workflows_repository, components_repository, components_service)

    async def list_workflows(
        self, filter: WorkflowListFilter, pagination: PaginatedList
    ) -> tuple[list[Workflow], int]:
        # browse-list callers always see only VALIDATED workflows - enforced here rather
        # than trusted from an arbitrary caller-supplied filter, so a public browse
        # request can never leak pending workflows regardless of what the router builds
        filter = replace(filter, status=WorkflowStatus.VALIDATED, created_by=None)
        return await self.workflows_repository.find_paginated(filter, pagination)

    async def list_my_workflows_by_status(
        self, created_by_id: uuid.UUID, status: WorkflowStatus, pagination: PaginatedList
    ) -> tuple[list[Workflow], int]:
        filter = WorkflowListFilter(created_by=created_by_id, status=status)
        return await self.workflows_repository.find_paginated(filter, pagination)

    async def get_latest_workflows(self, limit: int) -> list[Workflow]:
        # mirrors ComponentsService.get_latest_components - sort/slice in Python over the
        # already-fetched (VALIDATED-only) list rather than a SQL ORDER BY + LIMIT
        workflows = await self.workflows_repository.find_all()
        return sorted(workflows, key=lambda w: w.created_at, reverse=True)[:limit]

    async def get_workflow(self, workflow_id: uuid.UUID) -> Workflow:
        workflow = await self.workflows_repository.find_by_id(workflow_id)
        if workflow is None:
            raise WorkflowNotFoundError(workflow_id)
        return workflow

    async def get_visible_workflow(self, workflow_id: uuid.UUID, current_user: User | None) -> Workflow:
        workflow = await self.get_workflow(workflow_id)
        is_owner = current_user is not None and current_user.id == workflow.created_by_id
        if workflow.status == WorkflowStatus.PENDING_VALIDATION and not is_owner:
            # deliberately indistinguishable from "doesn't exist" to non-owners
            raise WorkflowNotFoundError(workflow_id)
        return workflow

    async def parse_workflow_upload(self, content: bytes, filename: str | None = None) -> WorkflowUploadPreview:
        """Analyse an uploaded workflow file without persisting anything - auto-detects
        whether `content` is a .zip archive or a bare .cwl file, then classifies it as
        external-only / self-contained / mixed. For a zip, also cross-references each
        step's external run: filename against the archive's own .cwl files.

        `filename` is the name of the uploaded file itself, used (with its .cwl extension
        stripped) as a fallback workflow name when the document has no `label:` - for a
        zip this is overridden by the name of the file that actually contains
        `class: Workflow`.
        """
        upload = self._load_upload_content(content, filename)

        try:
            overview = read_workflow_overview(upload.cwl_content)
        except ValueError as err:
            raise InvalidWorkflowCwlError(str(err)) from err

        self_contained = is_self_contained(upload.cwl_content)
        components = extract_inline_components(upload.cwl_content) if self_contained else []

        missing_external_refs = (
            sorted(ref for ref in set(overview.external_refs) if ref not in upload.available_files)
            if upload.available_files is not None
            else []
        )

        return WorkflowUploadPreview(
            is_zip=upload.is_zip,
            is_self_contained=self_contained,
            workflow_name=overview.name
            or (strip_cwl_extension(upload.pipeline_filename) if upload.pipeline_filename else None),
            step_count=overview.step_count,
            extracted_components=components,
            external_refs=overview.external_refs,
            unsupported_inline_steps=overview.unsupported_inline_steps,
            missing_external_refs=missing_external_refs,
        )

    def _load_upload_content(self, content: bytes, filename: str | None) -> WorkflowUploadContent:
        """Auto-detects whether `content` is a .zip archive or a bare .cwl file and
        locates the one `class: Workflow` document within it - shared by
        parse_workflow_upload and create_from_upload so the dispatch only lives once."""
        if zipfile.is_zipfile(BytesIO(content)):
            files = self._extract_zip_files(content)
            try:
                pipeline_filename, cwl_content = find_workflow_file(files)
            except ValueError as err:
                raise InvalidWorkflowArchiveError(str(err)) from err
            return WorkflowUploadContent(
                is_zip=True,
                cwl_content=cwl_content,
                pipeline_filename=pipeline_filename,
                available_files=set(files.keys()),
            )

        try:
            cwl_content = content.decode("utf-8")
        except UnicodeDecodeError as err:
            raise InvalidWorkflowCwlError("File is not valid UTF-8 text") from err
        return WorkflowUploadContent(
            is_zip=False, cwl_content=cwl_content, pipeline_filename=filename, available_files=None
        )

    async def _validate_extracted_component_names(self, names: list[str]) -> None:
        """Validates every final extracted-component name before creating any of them -
        blank check, duplicate-within-this-upload check, and a catalogue collision check.
        Necessary because ComponentsService.create_manual commits immediately per call
        (no shared transaction across N creates), so the common failure mode (a name
        collision) must fail atomically up front rather than being discovered mid-loop
        after earlier components are already permanently persisted."""
        seen: set[str] = set()
        for name in names:
            if not name.strip():
                raise InvalidExtractedComponentNameError(name)
            if name in seen:
                raise DuplicateExtractedComponentNameError(name)
            seen.add(name)
        for name in names:
            existing_versions = await self.components_repository.find_versions_by_name(name)
            if existing_versions:
                raise ExtractedComponentNameCollisionError(name)

    async def _parse_zip_into_steps(self, zip_bytes: bytes) -> tuple[str, list[WorkflowStep]]:
        """(pipeline CWL, fresh WorkflowStep rows) from an archive.

        Every step is fuzzy-matched against the current component catalogue. The returned
        steps are unsaved and unattached - the caller owns them into a Workflow.
        """
        files = self._extract_zip_files(zip_bytes)

        try:
            _pipeline_filename, pipeline_content = find_workflow_file(files)
        except ValueError as err:
            raise InvalidWorkflowArchiveError(str(err)) from err

        try:
            parsed_steps = extract_workflow_steps(pipeline_content)
        except ValueError as err:
            raise InvalidWorkflowArchiveError(str(err)) from err

        missing = [s.run_reference for s in parsed_steps if s.run_reference not in files]
        if missing:
            raise InvalidWorkflowArchiveError(f"Referenced step file(s) not found in archive: {', '.join(missing)}")

        # latest version per lineage of every existing Component - the fuzzy matcher
        # compares against lineage names, but the id returned still pins one specific version
        all_components = await self.components_repository.find_all()
        candidates = [(c.id, c.name) for c in all_components]

        steps: list[WorkflowStep] = []
        for parsed in parsed_steps:
            match = best_match(parsed.run_reference, candidates)
            if match is not None:
                component_id, _name, score = match
                steps.append(
                    WorkflowStep(
                        step_id=parsed.step_id,
                        run_reference=parsed.run_reference,
                        step_order=parsed.order,
                        component_id=component_id,
                        match_status=StepMatchStatus.SUGGESTED,
                        match_score=score,
                    )
                )
            else:
                steps.append(
                    WorkflowStep(
                        step_id=parsed.step_id,
                        run_reference=parsed.run_reference,
                        step_order=parsed.order,
                        match_status=StepMatchStatus.UNMATCHED,
                    )
                )

        return pipeline_content, steps

    async def create_from_zip(
        self,
        zip_bytes: bytes,
        name: str,
        description: str | None,
        domains: list[str],
        created_by_id: uuid.UUID,
        source: WorkflowSource = WorkflowSource.MANUAL_UPLOAD,
        draft_id: uuid.UUID | None = None,
    ) -> Workflow:
        pipeline_content, steps = await self._parse_zip_into_steps(zip_bytes)

        workflow = Workflow(
            name=name,
            description=description,
            created_by_id=created_by_id,
            cwl_content=pipeline_content,
            steps=steps,
            domains=[WorkflowDomain(domain=d) for d in domains],
            source=source,
            draft_id=draft_id,
        )
        return await self._save_and_reload(workflow)

    async def create_from_upload(
        self,
        content: bytes,
        filename: str | None,
        name: str,
        description: str | None,
        domains: list[str],
        component_domain: str | None,
        component_name_overrides: dict[str, str],
        created_by_id: uuid.UUID,
    ) -> Workflow:
        """Persists any of the 3 manual-upload shapes (external-only zip, self-contained
        bare .cwl, or a zip mixing both) as a real Workflow - and, for each inline
        CommandLineTool step, a real Component. component_name_overrides maps
        step_id -> user-edited name, falling back to the extracted suggested_name;
        component_domain applies to every extracted component in this upload
        (Component.domain is a single value, distinct from Workflow.domains) and is only
        required when the upload actually has inline steps to extract.
        """
        upload = self._load_upload_content(content, filename)

        try:
            overview = read_workflow_overview(upload.cwl_content)
        except ValueError as err:
            raise InvalidWorkflowCwlError(str(err)) from err

        if overview.unsupported_inline_steps:
            raise UnsupportedInlineWorkflowStepError(overview.unsupported_inline_steps)

        if not upload.is_zip and overview.external_refs:
            raise InvalidWorkflowCwlError(
                "A bare .cwl upload cannot reference external step files - upload a .zip archive instead"
            )
        if upload.available_files is not None:
            missing = sorted(ref for ref in set(overview.external_refs) if ref not in upload.available_files)
            if missing:
                raise InvalidWorkflowArchiveError(
                    f"Referenced step file(s) not found in archive: {', '.join(missing)}"
                )

        extracted_components = extract_inline_components(upload.cwl_content)
        if extracted_components and component_domain is None:
            raise ComponentDomainRequiredError()

        final_names = {
            extracted.step_id: component_name_overrides.get(extracted.step_id, extracted.suggested_name)
            for extracted in extracted_components
        }
        await self._validate_extracted_component_names(list(final_names.values()))

        run_references = {step_id: cwl_filename_for(final_name) for step_id, final_name in final_names.items()}
        pipeline_content = externalize_inline_steps(upload.cwl_content, run_references)

        extracted_by_step_id = {extracted.step_id: extracted for extracted in extracted_components}

        # latest version per lineage of every existing Component - same fuzzy-match
        # candidate pool as _parse_zip_into_steps, for the external-ref steps here
        all_components = await self.components_repository.find_all()
        candidates = [(c.id, c.name) for c in all_components]

        steps: list[WorkflowStep] = []
        pending_components: list[tuple[WorkflowStep, Component]] = []
        for order, (step_id, definition) in enumerate(extract_step_definitions(upload.cwl_content)):
            run_value = definition["run"]
            if isinstance(run_value, str):
                match = best_match(run_value, candidates)
                if match is not None:
                    component_id, _name, score = match
                    steps.append(
                        WorkflowStep(
                            step_id=step_id,
                            run_reference=run_value,
                            step_order=order,
                            component_id=component_id,
                            match_status=StepMatchStatus.SUGGESTED,
                            match_score=score,
                        )
                    )
                else:
                    steps.append(
                        WorkflowStep(
                            step_id=step_id,
                            run_reference=run_value,
                            step_order=order,
                            match_status=StepMatchStatus.UNMATCHED,
                        )
                    )
            else:
                # guaranteed class: CommandLineTool by the unsupported_inline_steps guard above
                extracted = extracted_by_step_id[step_id]
                component = Component(
                    name=final_names[step_id],
                    domain=component_domain,
                    cwl_content=inject_cwl_version(extracted.cwl_content, overview.cwl_version),
                    source=ComponentSource.MANUAL_UPLOAD,
                    created_by_id=created_by_id,
                    description=extracted.description,
                )
                # the mapping is exact - the tool *was* this step - not a fuzzy guess, so
                # it's CONFIRMED immediately and match_score stays None (no score to report)
                step = WorkflowStep(
                    step_id=step_id,
                    run_reference=run_references[step_id],
                    step_order=order,
                    match_status=StepMatchStatus.CONFIRMED,
                    match_score=None,
                )
                pending_components.append((step, component))
                steps.append(step)

        # only create Components once every validation above has passed - create_manual
        # commits immediately per call, so this loop is the point of no return
        for step, component in pending_components:
            created = await self.components_service.create_manual(component)
            step.component_id = created.id
            # also link the ORM relationship object itself (not just the FK id) - the
            # later commit()+refresh() in _save_and_reload expires every object in the
            # session, and without this, serialising step.component afterwards would
            # attempt a genuine lazy load outside of any async-safe context and crash
            # with MissingGreenlet
            step.component = created

        workflow = Workflow(
            name=name,
            description=description,
            created_by_id=created_by_id,
            cwl_content=pipeline_content,
            steps=steps,
            domains=[WorkflowDomain(domain=d) for d in domains],
            source=WorkflowSource.MANUAL_UPLOAD,
        )
        return await self._save_and_reload(workflow)

    async def upsert_from_draft(
        self,
        zip_bytes: bytes,
        name: str,
        draft_id: uuid.UUID,
        created_by_id: uuid.UUID,
    ) -> Workflow:
        """Keep exactly one Workflow in sync with a Builder draft.

        First publish of a draft creates the row; every later Save re-generates its CWL
        and steps in place. Re-syncing always drops the workflow back to
        PENDING_VALIDATION - the content changed, so its confirmed step matches (and any
        VALIDATED/public status) no longer describe it and it needs re-checking. The
        existing row is only reused when the caller owns it; anything else falls through
        to a fresh row.
        """
        existing = await self.workflows_repository.find_by_draft_id(draft_id)
        if existing is None or existing.created_by_id != created_by_id:
            return await self.create_from_zip(
                zip_bytes=zip_bytes,
                name=name,
                description=None,
                domains=[],
                created_by_id=created_by_id,
                source=WorkflowSource.WORKFLOW_BUILDER,
                draft_id=draft_id,
            )

        pipeline_content, steps = await self._parse_zip_into_steps(zip_bytes)
        existing.name = name
        existing.cwl_content = pipeline_content
        # cascade="all, delete-orphan" on Workflow.steps deletes the replaced rows
        existing.steps = steps
        existing.status = WorkflowStatus.PENDING_VALIDATION
        return await self._save_and_reload(existing)

    async def linked_workflow_ids(self, draft_ids: set[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
        """{draft_id: workflow_id} for the drafts that have a synced Workflow in My Workflows."""
        workflows = await self.workflows_repository.find_all_by_draft_ids(draft_ids)
        return {w.draft_id: w.id for w in workflows if w.draft_id is not None}

    async def delete_by_draft_id(self, draft_id: uuid.UUID, owner_id: uuid.UUID) -> bool:
        """Delete the Workflow synced from this draft, if one exists and the user owns it.

        Returns whether a row was removed. Used by the draft-delete flow when the user
        opts to also drop the My Workflows copy.
        """
        workflow = await self.workflows_repository.find_by_draft_id(draft_id)
        if workflow is None or workflow.created_by_id != owner_id:
            return False
        await self.workflows_repository.delete(workflow)
        return True

    async def get_step_with_workflow(self, step_id: uuid.UUID) -> tuple[WorkflowStep, Workflow]:
        step = await self.workflows_repository.find_step_by_id(step_id)
        if step is None:
            raise WorkflowStepNotFoundError(step_id)
        workflow = await self.get_workflow(step.workflow_id)
        return step, workflow

    async def update_step_component(self, step_id: uuid.UUID, component_id: uuid.UUID | None) -> WorkflowStep:
        step = await self.workflows_repository.find_step_by_id(step_id)
        if step is None:
            raise WorkflowStepNotFoundError(step_id)

        # selecting a candidate here never confirms it - only confirm_step() does. A
        # manually-touched selection also has no algorithmic confidence value, so
        # match_score is always cleared, whether a component was picked or cleared.
        if component_id is not None:
            component = await self.components_repository.find_by_id(component_id)
            if component is None:
                raise ComponentNotFoundError(component_id)
            step.component_id = component_id
            step.match_status = StepMatchStatus.SUGGESTED
            step.match_score = None
        else:
            step.component_id = None
            step.match_status = StepMatchStatus.UNMATCHED
            step.match_score = None

        saved_step = await self.workflows_repository.save_step(step)
        # a step edit can never re-publish a workflow, only un-publish an already-published
        # one whose steps are no longer all confirmed - publishing itself is a separate,
        # explicit creator action (see publish())
        await self._revert_to_pending_if_needed(saved_step.workflow_id)
        return saved_step

    async def confirm_step(self, step_id: uuid.UUID) -> WorkflowStep:
        step = await self.workflows_repository.find_step_by_id(step_id)
        if step is None:
            raise WorkflowStepNotFoundError(step_id)
        if step.component_id is None:
            raise WorkflowStepNotMatchedError(step_id)

        step.match_status = StepMatchStatus.CONFIRMED
        return await self.workflows_repository.save_step(step)

    async def publish(self, workflow: Workflow) -> Workflow:
        if workflow.status == WorkflowStatus.VALIDATED:
            return workflow
        if not all(s.match_status == StepMatchStatus.CONFIRMED for s in workflow.steps):
            raise WorkflowNotReadyToPublishError(workflow.id)
        workflow.status = WorkflowStatus.VALIDATED
        return await self.workflows_repository.save(workflow)

    async def unpublish(self, workflow: Workflow) -> Workflow:
        """Inverse of publish - returns the workflow to PENDING_VALIDATION, where only its
        creator can see it. Same end state as the automatic downgrade in
        _revert_to_pending_if_needed, but triggered explicitly rather than by a step edit.
        Idempotent: an already-pending workflow is returned untouched.
        """
        if workflow.status == WorkflowStatus.PENDING_VALIDATION:
            return workflow
        workflow.status = WorkflowStatus.PENDING_VALIDATION
        return await self.workflows_repository.save(workflow)

    async def update_description(self, workflow: Workflow, description: str | None) -> Workflow:
        workflow.description = description
        return await self.workflows_repository.save(workflow)

    async def execute_command(
        self,
        workflow: Workflow,
        command: WorkflowCommand,
        current_user_id: uuid.UUID,
        favorites_service: "FavoritesService",
    ) -> Workflow:
        match command.type:
            case WorkflowCommandType.ADD_FAVORITE:
                await favorites_service.add_workflow_favorite(current_user_id, workflow.id)
                return workflow
            case WorkflowCommandType.REMOVE_FAVORITE:
                await favorites_service.remove_workflow_favorite(current_user_id, workflow.id)
                return workflow
            case WorkflowCommandType.PUBLISH:
                return await self.publish(workflow)
            case WorkflowCommandType.UNPUBLISH:
                return await self.unpublish(workflow)
            case WorkflowCommandType.UPDATE_DESCRIPTION:
                return await self.update_description(workflow, command.description)

    async def execute_step_command(self, step: WorkflowStep, command: WorkflowStepCommand) -> WorkflowStep:
        match command.type:
            case WorkflowStepCommandType.CONFIRM:
                return await self.confirm_step(step.id)

    async def remove(self, workflow: Workflow) -> None:
        await self.workflows_repository.delete(workflow)

    async def get_download(self, workflow: Workflow) -> tuple[str, bytes]:
        # same archive layout and naming as the builder's "Export CWL" (assemble_cwl_zip).
        # Step files keep their stored run_reference - that is what the pipeline's `run:`
        # lines point at, so they cannot be renamed here.
        step_files = [
            (step.run_reference, step.component.cwl_content)
            for step in workflow.steps
            if step.component is not None
        ]
        return assemble_cwl_zip(workflow.name, workflow.cwl_content, step_files)

    def _extract_zip_files(self, zip_bytes: bytes) -> dict[str, str]:
        try:
            with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                bad_file = zf.testzip()
                if bad_file is not None:
                    raise InvalidWorkflowArchiveError(f"Corrupt file in archive: {bad_file}")
                result: dict[str, str] = {}
                for info in zf.infolist():
                    if info.is_dir() or not info.filename.lower().endswith(".cwl"):
                        continue
                    # flatten to basename - CWL run: references are filenames, not paths;
                    # tolerate a zip that wraps everything in a single top-level folder
                    basename = info.filename.rsplit("/", 1)[-1]
                    # skip macOS AppleDouble sidecar files (e.g. "._pipeline.cwl") and the
                    # __MACOSX/ dir Finder adds automatically when zipping - these mirror
                    # real filenames but hold binary resource-fork data, not CWL content
                    if basename.startswith("._") or info.filename.startswith("__MACOSX/"):
                        continue
                    try:
                        result[basename] = zf.read(info).decode("utf-8")
                    except UnicodeDecodeError as err:
                        raise InvalidWorkflowArchiveError(f"'{basename}' is not valid UTF-8 text") from err
                if not result:
                    raise InvalidWorkflowArchiveError("Archive contains no .cwl files")
                return result
        except zipfile.BadZipFile as err:
            raise InvalidWorkflowArchiveError("Not a valid zip archive") from err

    async def _revert_to_pending_if_needed(self, workflow_id: uuid.UUID) -> None:
        # only ever downgrades VALIDATED -> PENDING_VALIDATION when a step edit leaves it
        # no longer fully confirmed - never auto-promotes to VALIDATED, that only happens
        # via the explicit publish() action.
        workflow = await self.workflows_repository.find_by_id(workflow_id)
        assert workflow is not None
        if workflow.status != WorkflowStatus.VALIDATED:
            return
        all_confirmed = all(s.match_status == StepMatchStatus.CONFIRMED for s in workflow.steps)
        if not all_confirmed:
            workflow.status = WorkflowStatus.PENDING_VALIDATION
            await self.workflows_repository.save(workflow)

    async def _save_and_reload(self, workflow: Workflow) -> Workflow:
        saved = await self.workflows_repository.save(workflow)
        reloaded = await self.workflows_repository.find_by_id_with_steps(saved.id)
        assert reloaded is not None
        return reloaded
