import uuid
import zipfile
from dataclasses import dataclass, field, replace
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
    ConflictingAuxiliaryFileError,
    MissingImportedFileError,
    UnconfiguredWorkflowStepError,
    UnpublishableWorkflowComponentsError,
    WorkflowHasUnpublishedComponentsError,
    WorkflowNameAlreadyExistsError,
    WorkflowNotFoundError,
    WorkflowNotReadyToPublishError,
    WorkflowStepNotFoundError,
    WorkflowStepNotMatchedError,
)
from app.application.service.components_service import ComponentsService
from app.domain.models.component import Component, ComponentSource, ComponentStatus
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.component_file import ComponentFile
from app.domain.models.parameter import Parameter
from app.domain.models.user import User
from app.domain.models.workflow import Workflow, WorkflowSource, WorkflowStatus
from app.domain.models.workflow_domain import WorkflowDomain
from app.domain.models.workflow_file import WorkflowFile
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep
from app.domain.pagination.pagination import PaginatedList
from app.domain.repository.components_repository import ComponentsRepository
from app.domain.repository.workflow_draft_repository import WorkflowDraftRepository
from app.domain.repository.workflows_repository import WorkflowListFilter, WorkflowsRepository
from app.infrastructure.cwl.cwl_matcher import best_match
from app.infrastructure.cwl.cwl_parser import (
    collect_import_targets,
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


def _merge_auxiliary_files(sources: list[list]) -> list[tuple[str, str]]:
    """One (path, content) list from several file collections.

    The same type file legitimately arrives from the workflow and from each component that
    imports it - identical content, so de-duplication is right. Genuinely different content
    under one path has no correct answer, so it fails loudly rather than picking a winner.
    """
    merged: dict[str, str] = {}
    for files in sources:
        for file in files:
            existing = merged.get(file.path)
            if existing is not None and existing != file.content:
                raise ConflictingAuxiliaryFileError(file.path)
            merged[file.path] = file.content
    return sorted(merged.items())


#: step states that need no further action before a workflow can be published - either the
#: user confirmed the component, or the step runs inline and never had one to confirm
_SETTLED_STEP_STATUSES = {StepMatchStatus.CONFIRMED, StepMatchStatus.INLINE}

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
    inline_only_steps: list[str]
    missing_external_refs: list[str]
    #: $import/$include targets resolved from the archive - preserved with the workflow
    auxiliary_files: list[str]
    #: referenced but absent from the archive; blocks the save, like missing_external_refs
    missing_imports: list[str]


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
    #: the archive's non-.cwl text files, keyed by their path relative to the archive root
    #: rather than flattened like `files` - a $import writes a path, and that exact path
    #: has to resolve in the archive handed back on download
    aux_files: dict[str, str] = field(default_factory=dict)

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

    async def find_latest_by_name(self, name: str, exclude_id: uuid.UUID | None = None) -> Workflow | None:
        return await self.workflows_repository.find_latest_by_name(name, exclude_id)

    async def find_visible_latest_by_name(
        self, name: str, current_user: User | None, exclude_id: uuid.UUID | None = None
    ) -> Workflow | None:
        """The workflow holding this name, but only if the caller may see it.

        A pending workflow is owner-only, so naming it to another user would both leak it
        and hand them a link they cannot open. The name is taken either way -
        uq_workflows_name is global - so only the description is withheld, never the
        collision itself.
        """
        existing = await self.workflows_repository.find_latest_by_name(name, exclude_id)
        if existing is None:
            return None
        is_owner = current_user is not None and current_user.id == existing.created_by_id
        if existing.status == WorkflowStatus.PENDING_VALIDATION and not is_owner:
            return None
        return existing

    async def _require_name_available(self, name: str, exclude_id: uuid.UUID | None = None) -> None:
        """Enforces uq_workflows_name in the service, so a collision comes back as a clean
        409 rather than an IntegrityError from the database.

        `exclude_id` is what lets a builder draft re-sync keep the name it already has.
        """
        if await self.workflows_repository.find_latest_by_name(name, exclude_id) is not None:
            raise WorkflowNameAlreadyExistsError(name)

    async def get_visible_workflow(self, workflow_id: uuid.UUID, current_user: User | None) -> Workflow:
        workflow = await self.get_workflow(workflow_id)
        is_owner = current_user is not None and current_user.id == workflow.created_by_id
        if workflow.status == WorkflowStatus.PENDING_VALIDATION and not is_owner:
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

        # every document the upload will persist can pull in type definitions, so scan the
        # pipeline and each step file, not just the pipeline
        documents = [upload.cwl_content, *(upload.files or {}).values()]
        auxiliary, missing_imports = self._resolve_imports(documents, upload.aux_files)

        return WorkflowUploadPreview(
            is_zip=upload.is_zip,
            is_self_contained=self_contained,
            workflow_name=overview.name
            or (strip_cwl_extension(upload.pipeline_filename) if upload.pipeline_filename else None),
            step_count=overview.step_count,
            component_previews=await self._build_component_previews(upload, overview.cwl_version),
            external_refs=overview.external_refs,
            inline_only_steps=overview.inline_only_steps,
            missing_external_refs=missing_external_refs,
            auxiliary_files=sorted(auxiliary),
            missing_imports=missing_imports,
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
                    # inline_only_steps and rejected on create, never previewed
                    continue
                # preview exactly what would be persisted: inline tools carry no
                # cwlVersion of their own, so the parent workflow's is injected here too
                cwl_content = inject_cwl_version(inline.cwl_content, cwl_version)
                origin, run_reference = COMPONENT_ORIGIN_INLINE, None
                suggested_name = inline.suggested_name

            existing_versions = await self.components_repository.find_versions_by_name(suggested_name)
            parameters = self._safe_extract_parameters(cwl_content)
            await self.components_service.resolve_format_labels(cwl_content, parameters)
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
                    parameters=parameters,
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
                aux_files=self._extract_zip_aux_files(content),
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
        await self._require_name_available(name)
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
        await self._require_name_available(name)
        upload = self._load_upload_content(content, filename)

        try:
            overview = read_workflow_overview(upload.cwl_content)
        except ValueError as err:
            raise InvalidWorkflowCwlError(str(err)) from err

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

        # a bare .cwl has no archive to resolve against, so any import is unsatisfiable
        pipeline_imports = collect_import_targets(upload.cwl_content)
        if not upload.is_zip and pipeline_imports:
            raise InvalidWorkflowCwlError(
                "A bare .cwl upload cannot import other files - upload a .zip archive containing them instead"
            )
        documents = [upload.cwl_content, *(upload.files or {}).values()]
        auxiliary, missing_imports = self._resolve_imports(documents, upload.aux_files)
        if missing_imports:
            raise MissingImportedFileError(missing_imports)

        step_definitions = extract_step_definitions(upload.cwl_content)
        # inline-only steps (ExpressionTool / nested Workflow) stay embedded in the
        # pipeline and never become Components, so there is nothing to configure for them
        inline_only = set(overview.inline_only_steps)
        unconfigured = [
            step_id
            for step_id, _ in step_definitions
            if step_id not in component_configs and step_id not in inline_only
        ]
        if unconfigured:
            raise UnconfiguredWorkflowStepError(unconfigured)

        configurable_steps = [(sid, d) for sid, d in step_definitions if sid not in inline_only]
        await self._validate_component_configs(configurable_steps, component_configs)

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
            run_value = definition["run"]
            is_inline = not isinstance(run_value, str)

            if step_id in inline_only:
                # left exactly as the author wrote it: externalize_inline_steps skipped
                # this step (it isn't in run_references), so the pipeline still carries
                # the definition inline. run_reference is NOT NULL and there is no file
                # to point at, so it records what the step actually is - the parentheses
                # keep it from ever being mistaken for a filename.
                inline_class = run_value.get("class") if isinstance(run_value, dict) else None
                steps.append(
                    WorkflowStep(
                        step_id=step_id,
                        run_reference=f"(inline {inline_class or 'definition'})",
                        step_order=order,
                        match_status=StepMatchStatus.INLINE,
                        match_score=None,
                    )
                )
                continue

            config = component_configs[step_id]
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
                # a component stands alone in the catalogue, so it carries its own imports
                # rather than relying on the workflow it arrived with still being around
                files=self._files_for(cwl_content, auxiliary, ComponentFile),
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
            files=self._files_for(pipeline_content, auxiliary, WorkflowFile),
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

        # excludes itself: re-syncing a draft keeps the workflow's own name
        await self._require_name_available(name, exclude_id=existing.id)
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

    async def publish(
        self, workflow: Workflow, current_user_id: uuid.UUID, publish_components: bool = False
    ) -> Workflow:
        """Make a workflow public.

        A public workflow whose steps point at draft components would be broken for every
        other user - drafts are owner-only - so every component it uses must be published
        too. `publish_components` opts into publishing them as part of this action;
        without it the draft components are reported and nothing is changed.
        """
        if workflow.status == WorkflowStatus.VALIDATED:
            return workflow
        if not all(s.match_status in _SETTLED_STEP_STATUSES for s in workflow.steps):
            raise WorkflowNotReadyToPublishError(workflow.id)

        drafts = [
            step.component
            for step in workflow.steps
            if step.component is not None and step.component.status == ComponentStatus.DRAFT
        ]
        if drafts:
            foreign = sorted({c.name for c in drafts if c.created_by_id != current_user_id})
            if foreign:
                raise UnpublishableWorkflowComponentsError(foreign)
            if not publish_components:
                raise WorkflowHasUnpublishedComponentsError(sorted({c.name for c in drafts}))
            for component in drafts:
                await self.components_service.publish(component)

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
                return await self.publish(workflow, current_user_id, command.publish_components)
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
        # the pipeline's own imports plus every component's - a step tool may import a
        # type the pipeline itself never mentions
        sources = [workflow.files, *(s.component.files for s in workflow.steps if s.component is not None)]
        return assemble_cwl_zip(
            workflow.name, workflow.cwl_content, step_files, _merge_auxiliary_files(sources)
        )

    #: plausible $import/$include targets - all text, so an unrelated binary in the archive
    #: never has to be decoded just to be ignored
    _AUX_EXTENSIONS = (".yml", ".yaml", ".json")

    @staticmethod
    def _files_for(cwl_content: str, auxiliary: dict[str, str], model: type) -> list:
        """The auxiliary rows one document needs, transitively.

        Only what this document reaches: a workflow that imports nothing gets no rows even
        when a sibling step file imports plenty.
        """
        needed: dict[str, str] = {}
        pending = list(collect_import_targets(cwl_content))
        while pending:
            target = pending.pop()
            if target in needed or target not in auxiliary:
                continue
            needed[target] = auxiliary[target]
            pending.extend(collect_import_targets(auxiliary[target]))
        return [model(path=path, content=content) for path, content in sorted(needed.items())]

    def _extract_zip_aux_files(self, zip_bytes: bytes) -> dict[str, str]:
        """The archive's non-.cwl text files, keyed by path relative to the archive root.

        Deliberately NOT flattened the way _extract_zip_files is: `run:` references are
        filenames, but a $import writes a path, and rewriting `types/spatial.yml` to
        `spatial.yml` would leave the import pointing at nothing once the archive is
        rebuilt on download.

        A single wrapper folder (what Finder adds when you zip a directory) is stripped,
        so `SpatialClustering/types/spatial.yml` still resolves as `types/spatial.yml`.
        """
        try:
            with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                names = [
                    info.filename
                    for info in zf.infolist()
                    if not info.is_dir()
                    and not info.filename.startswith("__MACOSX/")
                    and not info.filename.rsplit("/", 1)[-1].startswith("._")
                ]
                prefix = self._common_wrapper_folder(names)

                result: dict[str, str] = {}
                for name in names:
                    if not name.lower().endswith(self._AUX_EXTENSIONS):
                        continue
                    path = name[len(prefix) :] if prefix and name.startswith(prefix) else name
                    try:
                        result[path] = zf.read(name).decode("utf-8")
                    except UnicodeDecodeError:
                        # not text after all - it cannot be a $import target, so skipping it
                        # is better than failing an upload over a file nothing references
                        continue
                return result
        except zipfile.BadZipFile as err:
            raise InvalidWorkflowArchiveError("Not a valid zip archive") from err

    @staticmethod
    def _common_wrapper_folder(names: list[str]) -> str:
        """`"SpatialClustering/"` when every entry sits under one top-level folder, else ""."""
        tops = {name.split("/", 1)[0] for name in names if "/" in name}
        if len(tops) != 1 or any("/" not in name for name in names):
            return ""
        return f"{tops.pop()}/"

    @staticmethod
    def _match_archive_path(target: str, files: dict[str, str]) -> str | None:
        """The archive entry a $import target refers to, tolerating layout differences."""
        if target in files:
            return target
        suffix = "/" + target
        matches = [path for path in files if path.endswith(suffix)]
        if len(matches) == 1:
            return matches[0]
        # last resort: the import writes a path the archive flattened (or vice versa)
        base = target.rsplit("/", 1)[-1]
        matches = [path for path in files if path.rsplit("/", 1)[-1] == base]
        return matches[0] if len(matches) == 1 else None

    def _resolve_imports(
        self, documents: list[str], aux_files: dict[str, str]
    ) -> tuple[dict[str, str], list[str]]:
        """({path: content} to preserve, sorted paths that could not be found).

        Follows imports transitively - an imported types file may import another - and
        keys each result under the path the document actually wrote, since that is what
        has to resolve on the way back out.
        """
        resolved: dict[str, str] = {}
        missing: set[str] = set()
        pending = [target for document in documents for target in collect_import_targets(document)]

        while pending:
            target = pending.pop()
            if target in resolved or target in missing:
                continue
            match = self._match_archive_path(target, aux_files)
            if match is None:
                missing.add(target)
                continue
            content = aux_files[match]
            resolved[target] = content
            pending.extend(collect_import_targets(content))

        return resolved, sorted(missing)

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
