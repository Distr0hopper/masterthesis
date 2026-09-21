import uuid
import zipfile
from dataclasses import dataclass, replace
from io import BytesIO
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from app.application.commands.commands import WorkflowCommand, WorkflowCommandType, WorkflowStepCommand, WorkflowStepCommandType
from app.application.exception.component_exceptions import ComponentNotFoundError
from app.application.exception.workflow_exceptions import (
    DuplicateExtractedComponentNameError,
    ExtractedComponentNameCollisionError,
    InvalidComponentConfigError,
    InvalidExtractedComponentNameError,
    InvalidWorkflowArchiveError,
    InvalidWorkflowCwlError,
    UnconfiguredWorkflowStepError,
    UnsupportedInlineWorkflowStepError,
    WorkflowNotFoundError,
    WorkflowNotReadyToPublishError,
    WorkflowStepNotFoundError,
    WorkflowStepNotMatchedError,
)
from app.application.service.components_service import ComponentsService
from app.domain.models.component import Component, ComponentSource
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.parameter import Parameter
from app.domain.models.user import User
from app.domain.models.workflow import Workflow, WorkflowSource, WorkflowStatus
from app.domain.models.workflow_domain import WorkflowDomain
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep
from app.domain.pagination.pagination import PaginatedList
from app.domain.repository.components_repository import ComponentsRepository
from app.domain.repository.workflow_draft_repository import WorkflowDraftRepository
from app.domain.repository.workflows_repository import WorkflowListFilter, WorkflowsRepository
from app.infrastructure.cwl.cwl_matcher import best_match
from app.infrastructure.cwl.cwl_parser import (
    extract_cwl_type,
    extract_description,
    extract_docker_pull,
    extract_dockerfile_content,
    extract_parameters,
    inject_cwl_version,
)
from app.infrastructure.cwl.workflow_generator import assemble_cwl_zip, cwl_filename_for
from app.infrastructure.cwl.workflow_parser import (
    externalize_inline_steps,
    extract_inline_components,
    extract_step_definitions,
    extract_workflow_steps,
    find_workflow_file,
    is_self_contained,
    read_workflow_overview,
    strip_cwl_extension,
)


#: an inline `run: {class: CommandLineTool}` lifted out of a self-contained workflow
COMPONENT_ORIGIN_INLINE = "inline"
#: a `run: some-tool.cwl` resolved against the uploaded archive's own files
COMPONENT_ORIGIN_ARCHIVE = "archive"


@dataclass
class ComponentMatch:
    """An existing catalogue Component a step could bind to instead of creating a new one -
    either because it shares the previewed name (name_conflict) or because the matcher
    scored it against the step's run: filename (suggested_match)."""

    component_id: uuid.UUID
    name: str
    version: int
    domains: list[str]
    #: fuzzy-match confidence; None for an exact name collision, which isn't a guess
    score: float | None


@dataclass
class ComponentPreview:
    """One workflow step rendered as the Component it would become - the whole point of
    the configure-before-save flow. Built for inline tools AND for the archive's own step
    files, which previously had their content thrown away after an existence check."""

    step_id: str
    origin: str
    #: the `run:` filename, archive origin only
    run_reference: str | None
    suggested_name: str
    description: str | None
    cwl_content: str
    cwl_type: str | None
    dockerfile_content: str | None
    docker_pull_reference: str | None
    parameters: list[Parameter]
    name_conflict: ComponentMatch | None
    suggested_match: ComponentMatch | None


@dataclass
class ComponentConfig:
    """The user's decision for one step: reuse an existing Component, or create a new one
    from the previewed CWL with this name/domain/description."""

    step_id: str
    reuse_component_id: uuid.UUID | None = None
    name: str | None = None
    domains: list[str] | None = None
    description: str | None = None

    @property
    def is_reuse(self) -> bool:
        return self.reuse_component_id is not None


@dataclass
class WorkflowUploadPreview:
    """Everything WorkflowsService.parse_workflow_upload reports back about one upload,
    which may be a bare .cwl file or a .zip archive - is_zip/missing_external_refs only
    apply to the zip case, [] otherwise."""

    is_zip: bool
    is_self_contained: bool
    workflow_name: str | None
    step_count: int
    component_previews: list[ComponentPreview]
    external_refs: list[str]
    unsupported_inline_steps: list[str]
    missing_external_refs: list[str]


@dataclass
class WorkflowUploadContent:
    """The zip-vs-bare-file dispatch result shared by parse_workflow_upload and
    create_from_upload - files is None for a bare .cwl upload (nothing to cross-check
    external refs against).

    NOTE: files holds the archive's full {filename: content} map, not just its keys -
    an external-ref step's own .cwl text is what gets previewed and, when the user opts
    to create rather than reuse, persisted as that step's Component.
    """

    is_zip: bool
    cwl_content: str
    pipeline_filename: str | None
    files: dict[str, str] | None

    @property
    def available_files(self) -> set[str] | None:
        return None if self.files is None else set(self.files)


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
        workflow_draft_repository: WorkflowDraftRepository,
    ):
        self.workflows_repository = workflows_repository
        self.components_repository = components_repository
        self.components_service = components_service
        self.workflow_draft_repository = workflow_draft_repository

    @staticmethod
    def get_service(
        workflows_repository: Annotated[WorkflowsRepository, Depends(WorkflowsRepository.get_repository)],
        components_repository: Annotated[ComponentsRepository, Depends(ComponentsRepository.get_repository)],
        components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
        workflow_draft_repository: Annotated[
            WorkflowDraftRepository, Depends(WorkflowDraftRepository.get_repository)
        ],
    ) -> "WorkflowsService":
        return WorkflowsService(
            workflows_repository, components_repository, components_service, workflow_draft_repository
        )

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
            component_previews=await self._build_component_previews(upload, overview.cwl_version),
            external_refs=overview.external_refs,
            unsupported_inline_steps=overview.unsupported_inline_steps,
            missing_external_refs=missing_external_refs,
        )

    async def _build_component_previews(
        self, upload: WorkflowUploadContent, cwl_version: str | None
    ) -> list[ComponentPreview]:
        """Every step of the upload rendered as the Component it would become.

        Covers both origins: inline CommandLineTools, and the archive's own step files -
        the latter used to be existence-checked and then discarded, which is why a zip's
        steps could never be previewed or imported. Steps that cannot be resolved to any
        CWL text (an external ref on a bare .cwl upload, or one missing from the archive)
        are skipped; read_workflow_overview's external_refs/missing_external_refs already
        report those, and create_from_upload rejects them outright.
        """
        inline_by_step_id = {c.step_id: c for c in extract_inline_components(upload.cwl_content)}

        # one query, reused for every archive step's fuzzy match - latest version per
        # lineage, the same candidate pool create_from_upload and _parse_zip_into_steps use
        all_components = await self.components_repository.find_all()
        candidates = [(c.id, c.name) for c in all_components]
        by_id = {c.id: c for c in all_components}

        previews: list[ComponentPreview] = []
        for step_id, definition in extract_step_definitions(upload.cwl_content):
            run_value = definition.get("run")
            suggested_match: ComponentMatch | None = None

            if isinstance(run_value, str):
                if upload.files is None or run_value not in upload.files:
                    continue
                cwl_content = upload.files[run_value]
                origin, run_reference = COMPONENT_ORIGIN_ARCHIVE, run_value
                suggested_name = strip_cwl_extension(run_value)
                match = best_match(run_value, candidates)
                if match is not None:
                    matched_id, _name, score = match
                    suggested_match = self._to_component_match(by_id[matched_id], score)
            else:
                inline = inline_by_step_id.get(step_id)
                if inline is None:
                    # an inline run: that isn't a CommandLineTool - reported separately as
                    # unsupported_inline_steps and rejected on create, never previewed
                    continue
                # preview exactly what would be persisted: inline tools carry no
                # cwlVersion of their own, so the parent workflow's is injected here too
                cwl_content = inject_cwl_version(inline.cwl_content, cwl_version)
                origin, run_reference = COMPONENT_ORIGIN_INLINE, None
                suggested_name = inline.suggested_name

            existing_versions = await self.components_repository.find_versions_by_name(suggested_name)
            previews.append(
                ComponentPreview(
                    step_id=step_id,
                    origin=origin,
                    run_reference=run_reference,
                    suggested_name=suggested_name,
                    description=extract_description(cwl_content),
                    cwl_content=cwl_content,
                    cwl_type=extract_cwl_type(cwl_content),
                    dockerfile_content=extract_dockerfile_content(cwl_content),
                    docker_pull_reference=extract_docker_pull(cwl_content),
                    parameters=self._safe_extract_parameters(cwl_content),
                    name_conflict=self._to_component_match(existing_versions[-1], None) if existing_versions else None,
                    suggested_match=suggested_match,
                )
            )
        return previews

    @staticmethod
    def _to_component_match(component: Component, score: float | None) -> ComponentMatch:
        return ComponentMatch(
            component_id=component.id,
            name=component.name,
            version=component.version,
            domains=sorted(d.domain for d in component.domains),
            score=score,
        )

    @staticmethod
    def _safe_extract_parameters(cwl_content: str) -> list[Parameter]:
        """Preview-only: a step file whose ports don't parse still deserves to be shown
        (with its CWL and Docker tabs intact) rather than failing the whole upload. The
        real parse happens again in ComponentsService.create_manual, which does raise."""
        try:
            return extract_parameters(cwl_content)
        except ValueError:
            return []

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
                files=files,
            )

        try:
            cwl_content = content.decode("utf-8")
        except UnicodeDecodeError as err:
            raise InvalidWorkflowCwlError("File is not valid UTF-8 text") from err
        return WorkflowUploadContent(
            is_zip=False, cwl_content=cwl_content, pipeline_filename=filename, files=None
        )

    async def _validate_component_configs(
        self, step_definitions: list[tuple[str, dict]], configs: dict[str, ComponentConfig]
    ) -> None:
        """Validates every step's configuration before any Component is created.

        Reuse configs only need their target to exist. Create configs get the full
        treatment: a domain, a non-blank name, no duplicate name within this upload, and
        no collision with the catalogue (the user is offered the reuse branch instead).

        Necessary because ComponentsService.create_manual commits immediately per call
        (no shared transaction across N creates), so the common failure mode (a name
        collision) must fail atomically up front rather than being discovered mid-loop
        after earlier components are already permanently persisted. This matters more now
        than it did before: archive steps create components too, so N is larger.
        """
        seen: set[str] = set()
        for step_id, _definition in step_definitions:
            config = configs[step_id]

            if config.is_reuse:
                if config.reuse_component_id is not None:
                    component = await self.components_repository.find_by_id(config.reuse_component_id)
                    if component is None:
                        raise ComponentNotFoundError(config.reuse_component_id)
                continue

            if config.name is None or not config.name.strip():
                raise InvalidExtractedComponentNameError(config.name or "")
            if not config.domains:
                raise InvalidComponentConfigError(step_id, "at least one domain is required to create a new component")
            if config.name in seen:
                raise DuplicateExtractedComponentNameError(config.name)
            seen.add(config.name)

        for step_id, _definition in step_definitions:
            config = configs[step_id]
            if config.is_reuse or config.name is None:
                continue
            existing_versions = await self.components_repository.find_versions_by_name(config.name)
            if existing_versions:
                raise ExtractedComponentNameCollisionError(config.name)

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
        component_configs: dict[str, ComponentConfig],
        created_by_id: uuid.UUID,
    ) -> Workflow:
        """Persists any of the 3 manual-upload shapes (external-only zip, self-contained
        bare .cwl, or a zip mixing both) as a real Workflow.

        Every step must carry a ComponentConfig (keyed by step_id, as previewed by
        parse_workflow_upload): either reuse_component_id, binding the step to an existing
        catalogue Component, or a name/domain/description to create a new one from that
        step's CWL. Nothing is auto-created behind the user's back and nothing is left to
        post-save fuzzy triage - an unconfigured step is an error, not a guess.
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

        step_definitions = extract_step_definitions(upload.cwl_content)
        unconfigured = [step_id for step_id, _ in step_definitions if step_id not in component_configs]
        if unconfigured:
            raise UnconfiguredWorkflowStepError(unconfigured)

        await self._validate_component_configs(step_definitions, component_configs)

        extracted_by_step_id = {c.step_id: c for c in extract_inline_components(upload.cwl_content)}

        # existence already guaranteed by _validate_component_configs above
        reused_components = {
            step_id: await self.components_repository.find_by_id(config.reuse_component_id)
            for step_id, config in component_configs.items()
            if config.reuse_component_id is not None
        }

        # every inline step gets its run: rewritten to a filename, including one bound to
        # an existing component (named after that component) - otherwise the stored
        # pipeline would keep an inline tool body that no longer describes the step. An
        # archive step is left alone: it already points at a real file that still carries
        # that name inside the zip, so renaming its Component must not rename the reference.
        run_references = {
            step_id: cwl_filename_for(
                reused_components[step_id].name
                if component_configs[step_id].is_reuse
                else component_configs[step_id].name
            )
            for step_id in extracted_by_step_id
        }
        pipeline_content = externalize_inline_steps(upload.cwl_content, run_references)

        steps: list[WorkflowStep] = []
        pending_components: list[tuple[WorkflowStep, Component]] = []
        for order, (step_id, definition) in enumerate(step_definitions):
            config = component_configs[step_id]
            run_value = definition["run"]
            is_inline = not isinstance(run_value, str)
            reference = run_references[step_id] if is_inline else run_value

            if config.is_reuse:
                steps.append(
                    WorkflowStep(
                        step_id=step_id,
                        run_reference=reference,
                        step_order=order,
                        component_id=config.reuse_component_id,
                        # the user picked this explicitly during configuration - there is
                        # nothing left to triage on the detail page, and no score to report
                        match_status=StepMatchStatus.CONFIRMED,
                        match_score=None,
                    )
                )
                continue

            if is_inline:
                extracted = extracted_by_step_id[step_id]
                cwl_content = inject_cwl_version(extracted.cwl_content, overview.cwl_version)
                fallback_description = extracted.description
            else:
                cwl_content = upload.files[run_value]
                fallback_description = extract_description(cwl_content)

            component = Component(
                name=config.name,
                domains=[ComponentDomain(domain=d) for d in (config.domains or [])],
                cwl_content=cwl_content,
                source=ComponentSource.MANUAL_UPLOAD,
                created_by_id=created_by_id,
                description=config.description or fallback_description,
            )
            step = WorkflowStep(
                step_id=step_id,
                run_reference=reference,
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

    async def remove(
        self, workflow: Workflow, deleted_by_id: uuid.UUID, delete_linked_draft: bool = False
    ) -> bool:
        """Delete a workflow, optionally taking the builder canvas it was synced from with it.

        Returns whether a linked draft was deleted too. The mirror of
        WorkflowDraftService.delete_draft's delete_linked_workflow: both directions of the
        draft <-> workflow link are opt-in, so neither side's delete silently destroys the
        other. Without it the draft survives as an orphan - still openable, but no longer
        offering "edit in builder" from a workflow that no longer exists.

        The workflow is deleted first: it is what the user actually asked to remove, so
        failing to reach the draft afterwards must not leave that undone.
        """
        # read before the row goes away - the FK is ON DELETE SET NULL on the workflow side,
        # so nothing else recovers which draft this came from
        draft_id = workflow.draft_id
        await self.workflows_repository.delete(workflow)

        if not delete_linked_draft or draft_id is None:
            return False

        draft = await self.workflow_draft_repository.find_by_id(draft_id)
        if draft is None or draft.created_by_id != deleted_by_id:
            return False

        await self.workflow_draft_repository.delete(draft)
        return True

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
