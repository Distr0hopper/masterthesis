import posixpath
import uuid
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from typing import Annotated

from fastapi import Depends

from app.application.commands.commands import ManualFormatLabel, WorkflowStepCommand, WorkflowStepCommandType
from app.application.exception.component_exceptions import (
    ComponentDeprecatedError,
    ComponentKindMismatchError,
    ComponentNotFoundError,
    PackagedToolCannotTakeUploadError,
)
from app.application.exception.workflow_exceptions import (
    DuplicateExtractedComponentNameError,
    ExtractedComponentNameCollisionError,
    InvalidComponentConfigError,
    InvalidExtractedComponentNameError,
    InvalidWorkflowArchiveError,
    InlineStepNotBindableError,
    InvalidWorkflowCwlError,
    MissingImportedFileError,
    PublishedWorkflowStepsLockedError,
    StepsEditedInBuilderError,
    UnconfiguredWorkflowStepError,
    WorkflowCycleError,
    WorkflowStepNotFoundError,
    WorkflowStepNotMatchedError,
)
from app.application.service.components_service import ComponentsService
from app.application.service.tools_service import ToolsService
from app.application.unit_of_work import UnitOfWork
from app.domain.composite import lifecycle
from app.domain.composite.tree import contains_lineage, would_create_cycle
from app.domain.models.component import Component, ComponentKind, ComponentSource, ComponentStatus
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.component_file import ComponentFile
from app.domain.models.parameter import Parameter
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep
from app.infrastructure.cwl.cwl_matcher import best_match
from app.infrastructure.cwl.cwl_parser import (
    collect_import_targets,
    extract_cwl_type,
    extract_description,
    extract_docker_pull,
    extract_dockerfile_content,
    extract_parameters,
    inject_cwl_version,
    same_cwl_document,
)
from app.infrastructure.cwl.workflow_generator import cwl_filename_for
from app.infrastructure.cwl.workflow_parser import (
    ArchiveStep,
    ExtractedComponent,
    externalize_inline_steps,
    extract_inline_components,
    extract_step_definitions,
    find_root_workflow,
    is_self_contained,
    is_workflow_cwl,
    match_archive_path,
    read_workflow_overview,
    resolve_run_reference,
    strip_cwl_extension,
    walk_archive_steps,
)
from app.infrastructure.db.unit_of_work import SqlUnitOfWork

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
    #: a name conflict may be held by a workflow; a suggested match is always a tool
    kind: ComponentKind
    name: str
    version: int
    domains: list[str]
    #: fuzzy-match confidence; None for an exact name collision, which isn't a guess
    score: float | None
    #: a name conflict may be held by a deprecated version - it can't be reused then
    status: ComponentStatus = ComponentStatus.PUBLISHED


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
    ontology_url: str | None
    parameters: list[Parameter]
    name_conflict: ComponentMatch | None
    suggested_match: ComponentMatch | None
    #: uploading a new version only - what the same step runs in the newest version
    previous: "PreviousStepComponent | None" = None
    #: a tool, or a nested workflow from the archive - configured the same way
    kind: ComponentKind = ComponentKind.TOOL
    #: the step_id of the nested workflow whose step first runs it - None at the top level
    parent_step_id: str | None = None
    #: every step path running it, step_id first - an archive file is one component however
    #: often it runs
    used_by: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PreviousStepComponent:
    """What a step of the uploaded new version ran in the workflow's newest version - so its
    configuration can start from there instead of from scratch."""

    component: Component
    #: the uploaded step's CWL is not the one that component holds
    cwl_changed: bool
    #: the step may become that tool's next version: the actor's own tool, not packaged
    #: from GitHub (those get versions from their repo)
    can_add_version: bool


@dataclass
class ComponentConfig:
    """The user's decision for one step: reuse an existing Component, add the previewed CWL
    as the next version of one of the actor's tools, or create a new one from it with this
    name/domain/description."""

    step_id: str
    reuse_component_id: uuid.UUID | None = None
    #: the tool the step's CWL becomes the next version of - name and domains are its lineage's
    new_version_of_id: uuid.UUID | None = None
    name: str | None = None
    domains: list[str] | None = None
    description: str | None = None
    format_labels: list[ManualFormatLabel] = field(default_factory=list)

    @property
    def is_reuse(self) -> bool:
        return self.reuse_component_id is not None

    @property
    def is_new_version(self) -> bool:
        return self.new_version_of_id is not None


@dataclass
class WorkflowUploadPreview:
    """Everything WorkflowsService.parse_workflow_upload reports back about one upload,
    which may be a bare .cwl file or a .zip archive - is_zip/missing_external_refs only
    apply to the zip case, [] otherwise."""

    is_zip: bool
    is_self_contained: bool
    workflow_name: str | None
    #: the workflow document's own doc: field - pre-fills the upload form's description
    description: str | None
    step_count: int
    component_previews: list[ComponentPreview]
    external_refs: list[str]
    inline_only_steps: list[str]
    missing_external_refs: list[str]
    #: $import/$include targets resolved from the archive - preserved with the workflow
    auxiliary_files: list[str]
    #: referenced but absent from the archive; blocks the save, like missing_external_refs
    missing_imports: list[str]
    #: workflow files in the archive the root never runs - left out of the upload
    unused_workflow_files: list[str] = field(default_factory=list)


@dataclass
class WorkflowUploadContent:
    """The zip-vs-bare-file dispatch result shared by parse_workflow_upload and
    create_from_upload - files is None for a bare .cwl upload (nothing to cross-check
    external refs against).

    NOTE: files holds the archive's full {path: content} map of .cwl documents, not just
    its keys - an external-ref step's own .cwl text is what gets previewed and, when the
    user opts to create rather than reuse, persisted as that step's Component.
    """

    is_zip: bool
    cwl_content: str
    pipeline_filename: str | None
    files: dict[str, str] | None
    #: the archive's non-.cwl text files, keyed by their path relative to the archive root
    #: - a $import writes a path, and that exact path has to resolve in the archive handed
    #: back on download
    aux_files: dict[str, str] = field(default_factory=dict)
    unused_workflows: list[str] = field(default_factory=list)

    @property
    def root_filename(self) -> str:
        return self.pipeline_filename or "workflow.cwl"

    @property
    def documents(self) -> dict[str, str]:
        """Every .cwl document by path - a bare upload is an archive of just itself."""
        return self.files if self.files is not None else {self.root_filename: self.cwl_content}


@dataclass
class UploadUnit:
    """One component an upload needs a decision for. Steps running the same archive file
    share one - a file becomes one component however often it runs - and so do the runs of
    an inline tool in a nested workflow that runs twice."""

    #: the config key: the path of the first step running it (see ArchiveStep.path) - the
    #: plain step_id at the top level
    key: str
    kind: ComponentKind
    origin: str
    #: archive origin only
    file: str | None
    #: what it is persisted with - an inline tool with its document's cwlVersion injected
    cwl_content: str
    #: inline origin only
    inline: ExtractedComponent | None
    #: every step path running it, `key` first
    usages: list[str]
    #: the unit of the nested workflow whose step first runs it - None at the top level
    parent_key: str | None


@dataclass(frozen=True)
class DocumentStep:
    """A step of one workflow document, with the unit it runs - None for an inline-only step
    or a filename the archive does not hold."""

    step_id: str
    definition: dict
    unit_key: str | None


@dataclass
class UploadPlan:
    """An upload's whole tree, read once: what has to be configured, and what the steps of
    the root and of every nested workflow run."""

    root: str
    steps: list[ArchiveStep]
    units: dict[str, UploadUnit]
    #: {archive path of a workflow document: its steps} - the root and each nested workflow
    documents: dict[str, list[DocumentStep]]
    #: {step path: the unit it runs}
    unit_of: dict[str, str]
    #: `run:` filenames the archive does not hold
    missing_refs: list[str]

    def active_units(self, configs: dict[str, "ComponentConfig"]) -> list[UploadUnit]:
        """The units the upload creates or binds. Everything below a nested workflow that
        reuses an existing component instead comes along with that one - unless it also
        runs somewhere else."""
        inactive: set[str] = set()
        active: set[str] = set()
        for step in self.steps:
            parent = step.parent_path
            if parent is not None and (parent in inactive or self._reused(parent, configs)):
                inactive.add(step.path)
                continue
            if step.path in self.unit_of:
                active.add(self.unit_of[step.path])
        return [unit for key, unit in self.units.items() if key in active]

    def _reused(self, path: str, configs: dict[str, "ComponentConfig"]) -> bool:
        config = configs.get(self.unit_of.get(path, ""))
        return config is not None and config.is_reuse


@dataclass(frozen=True)
class StepBinding:
    """One builder-canvas node as a workflow step: the canvas already says exactly which
    component version runs there, so nothing is matched or guessed."""

    step_id: str
    run_reference: str
    component_id: uuid.UUID


class WorkflowsService:
    """What only a workflow - the composite - does: being uploaded together with the tools
    its steps run, being synced from a builder canvas, and having its steps bound to child
    components. Everything shared with tools is ComponentsService's.

    create_from_upload, update_step_component and execute_step_command are use cases, each
    one transaction. upsert_from_draft is not: it runs inside the unit of work of
    WorkflowDraftService.sync_to_my_components."""

    def __init__(self, uow: UnitOfWork, components_service: ComponentsService, tools_service: ToolsService):
        self.uow = uow
        self.components_service = components_service
        self.tools_service = tools_service

    @staticmethod
    def get_service(
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
        components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
        tools_service: Annotated[ToolsService, Depends(ToolsService.get_service)],
    ) -> "WorkflowsService":
        return WorkflowsService(uow, components_service, tools_service)

    async def parse_workflow_upload(
        self,
        content: bytes,
        filename: str | None = None,
        parent: Component | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> WorkflowUploadPreview:
        """Analyse an uploaded workflow file without persisting anything - auto-detects
        whether `content` is a .zip archive or a bare .cwl file, then classifies it as
        external-only / self-contained / mixed. For a zip, also cross-references each
        step's external run: filename against the archive's own .cwl files.

        `filename` is the name of the uploaded file itself, used (with its .cwl extension
        stripped) as a fallback workflow name when the document has no `label:` - for a
        zip this is overridden by the name of the file that actually contains
        `class: Workflow`.

        With `parent` - the upload is to become its next version - every step also reports
        what the same step runs in the lineage's newest version (see PreviousStepComponent).
        """
        upload = self._load_upload_content(content, filename)

        try:
            overview = read_workflow_overview(upload.cwl_content)
        except ValueError as err:
            raise InvalidWorkflowCwlError(str(err)) from err

        self_contained = is_self_contained(upload.cwl_content)
        plan = self._plan_upload(upload)

        # every document the upload will persist can pull in type definitions, so scan the
        # pipeline, each nested workflow and each step file, not just the pipeline
        auxiliary, missing_imports = self._resolve_imports(self._plan_documents(plan, upload), upload.aux_files)

        return WorkflowUploadPreview(
            is_zip=upload.is_zip,
            is_self_contained=self_contained,
            workflow_name=overview.name
            or (
                strip_cwl_extension(posixpath.basename(upload.pipeline_filename))
                if upload.pipeline_filename
                else None
            ),
            description=extract_description(upload.cwl_content),
            step_count=overview.step_count,
            component_previews=await self._build_component_previews(
                plan, await self._previous_step_components(parent), actor_id
            ),
            external_refs=overview.external_refs,
            inline_only_steps=overview.inline_only_steps,
            # a bare .cwl has nothing to cross-check against - its refs are refused outright
            missing_external_refs=plan.missing_refs if upload.is_zip else [],
            # the archive files - documents in different folders spell one import differently
            auxiliary_files=sorted({match_archive_path(target, upload.aux_files) or target for target in auxiliary}),
            missing_imports=missing_imports,
            unused_workflow_files=upload.unused_workflows,
        )

    def _plan_upload(self, upload: WorkflowUploadContent) -> UploadPlan:
        """Reads the upload's tree - the root, and every workflow its steps run, at any depth
        - into the units to configure. Raises InvalidWorkflowCwlError for a nested document
        that is not a readable workflow, or workflows running each other in a cycle."""
        files = upload.documents
        try:
            steps = walk_archive_steps(upload.root_filename, files)
        except ValueError as err:
            raise InvalidWorkflowCwlError(str(err)) from err

        inline_by_document: dict[str, dict[str, ExtractedComponent]] = {}

        def inline_of(document: str) -> dict[str, ExtractedComponent]:
            if document not in inline_by_document:
                inline_by_document[document] = {c.step_id: c for c in extract_inline_components(files[document])}
            return inline_by_document[document]

        units: dict[str, UploadUnit] = {}
        key_of: dict[tuple[str, ...], str] = {}
        unit_of: dict[str, str] = {}
        missing: set[str] = set()
        for step in steps:
            run_value = step.definition["run"]
            unit: UploadUnit | None = None
            if isinstance(run_value, str):
                if step.target is None:
                    missing.add(run_value)
                    continue
                identity: tuple[str, ...] = ("file", step.target)
                if identity not in key_of:
                    content = files[step.target]
                    unit = UploadUnit(
                        key=step.path,
                        kind=ComponentKind.WORKFLOW if is_workflow_cwl(content) else ComponentKind.TOOL,
                        origin=COMPONENT_ORIGIN_ARCHIVE,
                        file=step.target,
                        cwl_content=content,
                        inline=None,
                        usages=[],
                        parent_key=None,
                    )
            else:
                inline = inline_of(step.document).get(step.step_id)
                if inline is None:
                    # an inline run: that isn't a CommandLineTool stays embedded - see
                    # read_workflow_overview's inline_only_steps
                    continue
                identity = ("inline", step.document, step.step_id)
                if identity not in key_of:
                    unit = UploadUnit(
                        key=step.path,
                        kind=ComponentKind.TOOL,
                        origin=COMPONENT_ORIGIN_INLINE,
                        file=None,
                        # what is persisted: inline tools carry no cwlVersion of their own,
                        # so the document's is injected
                        cwl_content=inject_cwl_version(inline.cwl_content, self._cwl_version(files[step.document])),
                        inline=inline,
                        usages=[],
                        parent_key=None,
                    )
            if unit is not None:
                unit.parent_key = unit_of.get(step.parent_path) if step.parent_path else None
                units[unit.key] = unit
                key_of[identity] = unit.key
            key = key_of[identity]
            units[key].usages.append(step.path)
            unit_of[step.path] = key

        documents: dict[str, list[DocumentStep]] = {}
        workflow_files = [u.file for u in units.values() if u.kind == ComponentKind.WORKFLOW and u.file]
        for document in [upload.root_filename, *workflow_files]:
            document_steps: list[DocumentStep] = []
            for step_id, definition in extract_step_definitions(files[document]):
                run_value = definition["run"]
                if isinstance(run_value, str):
                    target = resolve_run_reference(run_value, document, files)
                    identity = ("file", target) if target is not None else ()
                else:
                    identity = ("inline", document, step_id)
                document_steps.append(DocumentStep(step_id, definition, key_of.get(identity)))
            documents[document] = document_steps

        return UploadPlan(
            root=upload.root_filename,
            steps=steps,
            units=units,
            documents=documents,
            unit_of=unit_of,
            missing_refs=sorted(missing),
        )

    @staticmethod
    def _cwl_version(cwl_content: str) -> str | None:
        try:
            return read_workflow_overview(cwl_content).cwl_version
        except ValueError:
            return None

    @staticmethod
    def _plan_documents(plan: UploadPlan, upload: WorkflowUploadContent) -> list[str]:
        """The CWL of every document the upload would persist - an unused workflow file in
        the archive is not one of them."""
        return [upload.cwl_content, *(u.cwl_content for u in plan.units.values() if u.file is not None)]

    async def _previous_step_components(self, parent: Component | None) -> dict[str, Component]:
        """{step path: component} of the newest version of `parent`'s lineage, nested
        workflows' steps included - {} without one."""
        if parent is None:
            return {}
        head = (await self.uow.components.find_versions_by_name(parent.name))[-1]
        head = await self.uow.components.find_by_id(head.id) or head
        await self.components_service.load_tree(head)

        result: dict[str, Component] = {}

        def visit(component: Component, prefix: str) -> None:
            for step in component.steps:
                if step.component is None:
                    continue
                path = f"{prefix}{step.step_id}"
                result[path] = step.component
                if step.component.is_workflow:
                    visit(step.component, f"{path}/")

        visit(head, "")
        return result

    async def _build_component_previews(
        self,
        plan: UploadPlan,
        previous_by_path: dict[str, Component] | None = None,
        actor_id: uuid.UUID | None = None,
    ) -> list[ComponentPreview]:
        """Every unit of the upload rendered as the Component it would become - inline
        CommandLineTools, the archive's step files and its nested workflows, in tree order.

        Steps that cannot be resolved to any CWL text (an external ref on a bare .cwl
        upload, or one missing from the archive) are skipped; missing_external_refs
        reports those, and create_from_upload rejects them outright.
        """
        # one query per kind, reused for every archive file's fuzzy match - the latest listed
        # version of every lineage. Listed only: a deprecated version takes no new
        # dependents, so it is never suggested
        candidates: dict[ComponentKind, list[Component]] = {
            kind: await self.uow.components.find_all(lifecycle.LISTED_STATUSES, kind)
            for kind in (ComponentKind.TOOL, ComponentKind.WORKFLOW)
        }
        by_id = {c.id: c for components in candidates.values() for c in components}

        previews: list[ComponentPreview] = []
        for unit in plan.units.values():
            suggested_match: ComponentMatch | None = None
            if unit.file is not None:
                run_filename = posixpath.basename(unit.file)
                suggested_name = strip_cwl_extension(run_filename)
                match = best_match(run_filename, [(c.id, c.name) for c in candidates[unit.kind]])
                if match is not None:
                    matched_id, _name, score = match
                    suggested_match = self._to_component_match(by_id[matched_id], score)
            else:
                assert unit.inline is not None
                suggested_name = unit.inline.suggested_name

            cwl_content = unit.cwl_content
            existing = await self.uow.components.find_latest_by_name(suggested_name)
            parameters = self._safe_extract_parameters(cwl_content)
            ontology_url = self.components_service.ontology_url_for(cwl_content)
            await self.components_service.resolve_format_labels(ontology_url, parameters)
            previews.append(
                ComponentPreview(
                    step_id=unit.key,
                    origin=unit.origin,
                    run_reference=unit.file,
                    suggested_name=suggested_name,
                    description=extract_description(cwl_content),
                    cwl_content=cwl_content,
                    cwl_type=extract_cwl_type(cwl_content),
                    dockerfile_content=extract_dockerfile_content(cwl_content),
                    docker_pull_reference=extract_docker_pull(cwl_content),
                    ontology_url=ontology_url,
                    parameters=parameters,
                    name_conflict=self._to_component_match(existing, None) if existing is not None else None,
                    suggested_match=suggested_match,
                    previous=self._previous_step_component(
                        (previous_by_path or {}).get(unit.key), cwl_content, actor_id
                    ),
                    kind=unit.kind,
                    parent_step_id=unit.parent_key,
                    used_by=list(unit.usages),
                )
            )
        return previews

    @staticmethod
    def _previous_step_component(
        component: Component | None, cwl_content: str, actor_id: uuid.UUID | None
    ) -> PreviousStepComponent | None:
        if component is None:
            return None
        return PreviousStepComponent(
            component=component,
            cwl_changed=not same_cwl_document(cwl_content, component.cwl_content),
            can_add_version=component.is_tool
            and not component.is_packaged
            and actor_id is not None
            and component.created_by_id == actor_id,
        )

    @staticmethod
    def _to_component_match(component: Component, score: float | None) -> ComponentMatch:
        return ComponentMatch(
            component_id=component.id,
            kind=ComponentKind(component.kind),
            name=component.name,
            version=component.version,
            domains=sorted(d.domain for d in component.domains),
            score=score,
            status=ComponentStatus(component.status),
        )

    @staticmethod
    def _safe_extract_parameters(cwl_content: str) -> list[Parameter]:
        """Preview-only: a step file whose ports don't parse still deserves to be shown
        (with its CWL and Docker tabs intact) rather than failing the whole upload. The
        real parse happens again in ToolsService.create_tool, which does raise."""
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
                root = find_root_workflow(files)
            except ValueError as err:
                raise InvalidWorkflowArchiveError(str(err)) from err
            return WorkflowUploadContent(
                is_zip=True,
                cwl_content=root.content,
                pipeline_filename=root.filename,
                files=files,
                aux_files=self._extract_zip_aux_files(content),
                unused_workflows=root.unused_workflows,
            )

        try:
            cwl_content = content.decode("utf-8")
        except UnicodeDecodeError as err:
            raise InvalidWorkflowCwlError("File is not valid UTF-8 text") from err
        return WorkflowUploadContent(
            is_zip=False, cwl_content=cwl_content, pipeline_filename=filename, files=None
        )

    async def _validate_component_configs(
        self,
        units: list[UploadUnit],
        configs: dict[str, ComponentConfig],
        actor_id: uuid.UUID,
        workflow_name: str,
    ) -> None:
        """Validates every unit's configuration before any Component is created.

        Reuse configs need a target the actor may bind (see _require_bindable) that does not
        already contain the uploaded workflow. Create configs get the full treatment: a
        domain, a non-blank name, no duplicate name within this upload - the workflow's own
        included - and no collision with the catalogue (the user is offered the reuse branch
        instead). Only a tool can take the step's CWL as its next version.

        Not needed for atomicity - the whole upload is one transaction - but it reports
        every configuration problem as the specific error the upload form understands,
        before any CWL is processed.
        """
        seen: set[str] = {workflow_name}
        versioned: set[str] = set()
        for unit in units:
            step_id = unit.key
            config = configs[step_id]

            if config.is_new_version:
                if unit.kind == ComponentKind.WORKFLOW:
                    raise InvalidComponentConfigError(
                        step_id, "a nested workflow is reused or created - only a tool gets a new version here"
                    )
                assert config.new_version_of_id is not None
                target = await self.uow.components.find_by_id(config.new_version_of_id)
                if target is None:
                    raise ComponentNotFoundError(config.new_version_of_id)
                if not target.is_tool or target.created_by_id != actor_id:
                    raise InvalidComponentConfigError(step_id, "only your own tools can get a new version here")
                if target.is_packaged:
                    raise PackagedToolCannotTakeUploadError(target.name)
                # one upload, one next version per lineage - a second would fight over the number
                if target.name in versioned:
                    raise InvalidComponentConfigError(
                        step_id, f"'{target.name}' already gets its next version from another step"
                    )
                versioned.add(target.name)
                continue

            if config.is_reuse:
                assert config.reuse_component_id is not None
                component = await self.uow.components.find_by_id(config.reuse_component_id)
                if component is None:
                    raise ComponentNotFoundError(config.reuse_component_id)
                self._require_bindable(component, actor_id)
                if component.is_workflow:
                    await self.components_service.load_tree(component)
                    if contains_lineage(component, workflow_name):
                        raise WorkflowCycleError(workflow_name, component.name)
                continue

            if config.name is None or not config.name.strip():
                raise InvalidExtractedComponentNameError(config.name or "")
            if not config.domains:
                raise InvalidComponentConfigError(step_id, "at least one domain is required to create a new component")
            if config.name in seen:
                raise DuplicateExtractedComponentNameError(config.name)
            seen.add(config.name)

        for unit in units:
            config = configs[unit.key]
            if config.is_reuse or config.is_new_version or config.name is None:
                continue
            # names are one key across both kinds, so a workflow's name collides too
            if await self.uow.components.find_latest_by_name(config.name) is not None:
                raise ExtractedComponentNameCollisionError(config.name)

    async def create_from_upload(
        self,
        content: bytes,
        filename: str | None,
        name: str,
        description: str | None,
        domains: list[str],
        component_configs: dict[str, ComponentConfig],
        created_by_id: uuid.UUID,
    ) -> Component:
        """Persists any of the 3 manual-upload shapes (external-only zip, self-contained
        bare .cwl, or a zip mixing both) as a real Workflow - see _persist_upload."""
        await self.components_service.require_name_available(name)
        return await self._persist_upload(
            content, filename, name, description, domains, component_configs, created_by_id
        )

    async def add_version_from_upload(
        self,
        parent: Component,
        content: bytes,
        filename: str | None,
        description: str | None,
        component_configs: dict[str, ComponentConfig],
        actor_id: uuid.UUID,
    ) -> Component:
        """An uploaded workflow as the next version of `parent`'s lineage - its name and
        domains, the next number. Starts as a draft, like every new version; publishing it
        supersedes the older ones.

        Not for a workflow still edited in the builder: its versions come from saving the
        canvas, and an upload would diverge from it."""
        if not parent.is_workflow:
            raise ComponentKindMismatchError(parent.name, ComponentKind(parent.kind).value)
        head = (await self.uow.components.find_versions_by_name(parent.name))[-1]
        if lifecycle.edited_in_builder(head):
            raise StepsEditedInBuilderError(head.id)
        return await self._persist_upload(
            content,
            filename,
            head.name,
            description,
            [d.domain for d in head.domains],
            component_configs,
            actor_id,
            version=head.version + 1,
        )

    async def _persist_upload(
        self,
        content: bytes,
        filename: str | None,
        name: str,
        description: str | None,
        domains: list[str],
        component_configs: dict[str, ComponentConfig],
        created_by_id: uuid.UUID,
        version: int = 1,
    ) -> Component:
        """An upload as workflow `name` v`version`.

        Every unit must carry a ComponentConfig (keyed by the step_id parse_workflow_upload
        previewed it under): reuse_component_id, binding its steps to an existing catalogue
        Component; new_version_of_id, adding its CWL as the next version of one of the
        actor's tools; or a name/domain/description to create a new one from it. Nothing is
        auto-created behind the user's back and nothing is left to post-save fuzzy triage -
        an unconfigured step is an error, not a guess.

        A nested workflow from the archive is a unit like any tool: created from its file -
        its own steps configured the same way, below it - or bound to an existing workflow,
        which then brings its steps along.
        """
        upload = self._load_upload_content(content, filename)

        try:
            overview = read_workflow_overview(upload.cwl_content)
        except ValueError as err:
            raise InvalidWorkflowCwlError(str(err)) from err

        if not upload.is_zip and overview.external_refs:
            raise InvalidWorkflowCwlError(
                "A bare .cwl upload cannot reference external step files - upload a .zip archive instead"
            )
        plan = self._plan_upload(upload)
        if plan.missing_refs:
            raise InvalidWorkflowArchiveError(
                f"Referenced step file(s) not found in archive: {', '.join(plan.missing_refs)}"
            )

        # a bare .cwl has no archive to resolve against, so any import is unsatisfiable
        if not upload.is_zip and collect_import_targets(upload.cwl_content):
            raise InvalidWorkflowCwlError(
                "A bare .cwl upload cannot import other files - upload a .zip archive containing them instead"
            )
        auxiliary, missing_imports = self._resolve_imports(self._plan_documents(plan, upload), upload.aux_files)
        if missing_imports:
            raise MissingImportedFileError(missing_imports)

        # inline-only steps (ExpressionTool / inline Workflow) stay embedded in their
        # document and never become Components, so there is nothing to configure for them -
        # nor for anything below a nested workflow that reuses an existing one
        units = plan.active_units(component_configs)
        unconfigured = [unit.key for unit in units if unit.key not in component_configs]
        if unconfigured:
            raise UnconfiguredWorkflowStepError(unconfigured)
        await self._validate_component_configs(units, component_configs, created_by_id, name)

        # existence already guaranteed by _validate_component_configs above
        reused: dict[str, Component] = {}
        versioned_tools: dict[str, Component] = {}
        for unit in units:
            config = component_configs[unit.key]
            if config.reuse_component_id is not None:
                reused[unit.key] = await self.uow.components.find_by_id(config.reuse_component_id)  # type: ignore[assignment]
            if config.new_version_of_id is not None:
                versioned_tools[unit.key] = await self.uow.components.find_by_id(config.new_version_of_id)  # type: ignore[assignment]

        def lineage_name(key: str) -> str | None:
            """The name the unit's component goes by - an existing lineage's, or the new one's."""
            if key in reused:
                return reused[key].name
            if key in versioned_tools:
                return versioned_tools[key].name
            return component_configs[key].name

        created: dict[str, Component] = {}

        async def component_for(key: str) -> Component:
            """The component a unit becomes - created once, however many steps run it."""
            if key in reused:
                return reused[key]
            if key in created:
                return created[key]
            unit, config = plan.units[key], component_configs[key]
            if unit.kind == ComponentKind.WORKFLOW:
                assert unit.file is not None and config.name is not None
                component = await persist_document(
                    unit.file,
                    config.name,
                    config.description or extract_description(unit.cwl_content),
                    config.domains or [],
                )
            else:
                target = versioned_tools.get(key)
                tool = Component(
                    kind=ComponentKind.TOOL,
                    # a next version keeps its lineage's name, domains and credits
                    name=target.name if target is not None else config.name,
                    domains=[
                        ComponentDomain(domain=d)
                        for d in ([d.domain for d in target.domains] if target is not None else (config.domains or []))
                    ],
                    author_name=target.author_name if target is not None else None,
                    cwl_content=unit.cwl_content,
                    source=ComponentSource.MANUAL_UPLOAD,
                    created_by_id=created_by_id,
                    description=config.description
                    or (unit.inline.description if unit.inline is not None else extract_description(unit.cwl_content)),
                    # a component stands alone in the catalogue, so it carries its own imports
                    # rather than relying on the workflow it arrived with still being around
                    files=self._files_for(unit.cwl_content, auxiliary),
                )
                component = (
                    await self.tools_service.add_uploaded_version_in_transaction(tool, config.format_labels)
                    if target is not None
                    else await self.tools_service.create_tool(tool, format_labels=config.format_labels)
                )
            created[key] = component
            return component

        async def persist_document(
            document: str, workflow_name: str, workflow_description: str | None, workflow_domains: list[str], at_version: int = 1
        ) -> Component:
            """One workflow document of the tree as a workflow - what its steps run first."""
            steps: list[WorkflowStep] = []
            # every inline step gets its run: rewritten to a filename, including one bound
            # to an existing component (named after that component) - otherwise the stored
            # pipeline would keep an inline tool body that no longer describes the step. An
            # archive step is left alone: it already points at a real file that still
            # carries that name inside the zip, so renaming its Component must not rename
            # the reference.
            run_references: dict[str, str] = {}
            for order, document_step in enumerate(plan.documents[document]):
                run_value = document_step.definition["run"]
                if document_step.unit_key is None:
                    # left exactly as the author wrote it - run_reference is NOT NULL and
                    # there is no file to point at, so it records what the step actually
                    # is; the parentheses keep it from ever being mistaken for a filename
                    inline_class = run_value.get("class") if isinstance(run_value, dict) else None
                    steps.append(
                        WorkflowStep(
                            step_id=document_step.step_id,
                            run_reference=f"(inline {inline_class or 'definition'})",
                            step_order=order,
                            match_status=StepMatchStatus.INLINE,
                            match_score=None,
                        )
                    )
                    continue

                unit = plan.units[document_step.unit_key]
                if unit.origin == COMPONENT_ORIGIN_INLINE:
                    reference = cwl_filename_for(lineage_name(unit.key))  # type: ignore[arg-type]
                    run_references[document_step.step_id] = reference
                else:
                    reference = run_value
                child = await component_for(unit.key)
                steps.append(
                    WorkflowStep(
                        step_id=document_step.step_id,
                        run_reference=reference,
                        step_order=order,
                        component_id=child.id,
                        component=child,
                        # the user decided every step during configuration - there is
                        # nothing left to triage on the detail page, and no score to report
                        match_status=StepMatchStatus.CONFIRMED,
                        match_score=None,
                    )
                )

            source = upload.documents[document]
            pipeline_content = externalize_inline_steps(source, run_references) if run_references else source
            return await self._create_workflow(
                name=workflow_name,
                description=workflow_description,
                domains=workflow_domains,
                created_by_id=created_by_id,
                pipeline_content=pipeline_content,
                steps=steps,
                source=ComponentSource.MANUAL_UPLOAD,
                files=self._files_for(pipeline_content, auxiliary),
                version=at_version,
            )

        # one transaction: the new tools, the nested workflows and the workflow are created
        # together or not at all
        async with self.uow:
            workflow = await persist_document(plan.root, name, description, domains, version)
            await self.uow.commit()
        return await self.components_service.reload(workflow)

    async def upsert_from_draft(
        self,
        pipeline_content: str,
        bindings: list[StepBinding],
        name: str,
        draft_id: uuid.UUID,
        created_by_id: uuid.UUID,
    ) -> Component:
        """Keep a workflow lineage in sync with a builder draft.

        The first sync of a draft creates version 1; every later Save re-generates the
        newest version's CWL and steps - in place while it was never published, or as the
        next version once it was, since a published version is what other users saw (and
        nested) and must not change under them - not even after it is unpublished again. The lineage is only reused when the
        caller owns it; anything else falls through to a fresh one.

        Runs inside the caller's unit of work and returns the workflow unreloaded - reload
        it after the commit.
        """
        steps = [
            WorkflowStep(
                step_id=binding.step_id,
                run_reference=binding.run_reference,
                step_order=order,
                component_id=binding.component_id,
                # the user placed exactly this component on the canvas - nothing to confirm
                match_status=StepMatchStatus.CONFIRMED,
            )
            for order, binding in enumerate(bindings)
        ]

        latest = await self.uow.workflows.find_latest_by_draft_id(draft_id)
        if latest is None or latest.created_by_id != created_by_id:
            await self.components_service.require_name_available(name)
            # the canvas asks for no domains - the owner sets them before publishing
            return await self._create_workflow(
                name=name,
                description=None,
                domains=[],
                created_by_id=created_by_id,
                pipeline_content=pipeline_content,
                steps=steps,
                source=ComponentSource.WORKFLOW_BUILDER,
                draft_id=draft_id,
            )

        if latest.name != name:
            # the name is the lineage key, so a renamed canvas renames every version
            await self.components_service.require_name_available(name, exclude_id=latest.id)
            await self.uow.components.rename_lineage(latest.name, name)
            # the bulk UPDATE bypassed the identity map - repopulate what it changed
            latest = await self.uow.components.find_by_id_fresh(latest.id)
            assert latest is not None
        await self._require_acyclic(latest, [b.component_id for b in bindings])

        if lifecycle.is_draft(latest):
            latest.cwl_content = pipeline_content
            # cascade="all, delete-orphan" on Workflow.steps / Component.parameters deletes
            # the replaced rows
            latest.workflow.steps = steps
            await self.components_service.assign_ports(latest, "Workflow")
            return await self.uow.components.add(latest)

        versions = await self.uow.components.find_versions_by_name(latest.name)
        return await self._create_workflow(
            name=latest.name,
            description=latest.description,
            domains=[d.domain for d in latest.domains],
            created_by_id=created_by_id,
            pipeline_content=pipeline_content,
            steps=steps,
            source=ComponentSource.WORKFLOW_BUILDER,
            draft_id=draft_id,
            version=versions[-1].version + 1,
        )

    async def _create_workflow(
        self,
        name: str,
        description: str | None,
        domains: list[str],
        created_by_id: uuid.UUID,
        pipeline_content: str,
        steps: list[WorkflowStep],
        source: ComponentSource,
        files: list[ComponentFile] | None = None,
        draft_id: uuid.UUID | None = None,
        version: int = 1,
    ) -> Component:
        workflow = Component(
            kind=ComponentKind.WORKFLOW,
            name=name,
            version=version,
            description=description,
            created_by_id=created_by_id,
            cwl_content=pipeline_content,
            source=source,
            domains=[ComponentDomain(domain=d) for d in domains],
            files=files or [],
            workflow=Workflow(steps=steps, draft_id=draft_id),
        )
        # a workflow's ports are its own inputs/outputs - what a parent sees when nesting it
        await self.components_service.assign_ports(workflow, "Workflow")
        return await self.uow.components.add(workflow)

    async def _require_acyclic(self, parent: Component, child_ids: list[uuid.UUID]) -> None:
        """Raises WorkflowCycleError when one of the children (eventually) runs `parent`."""
        for child in await self.uow.components.find_by_ids(list(dict.fromkeys(child_ids))):
            if not child.is_workflow:
                continue
            await self.components_service.load_tree(child)
            if would_create_cycle(parent, child):
                raise WorkflowCycleError(parent.name, child.name)

    async def linked_workflows(self, draft_ids: set[uuid.UUID]) -> dict[uuid.UUID, Component]:
        """{draft_id: newest workflow version} for the drafts synced to My Components."""
        workflows = await self.uow.workflows.find_all_by_draft_ids(draft_ids)
        return {w.workflow.draft_id: w for w in workflows if w.workflow is not None and w.workflow.draft_id}

    async def get_step_with_workflow(self, step_id: uuid.UUID) -> tuple[WorkflowStep, Component]:
        step = await self.uow.workflows.find_step_by_id(step_id)
        if step is None or step.parent is None:
            raise WorkflowStepNotFoundError(step_id)
        return step, step.parent

    async def update_step_component(
        self, step_id: uuid.UUID, component_id: uuid.UUID | None, actor_id: uuid.UUID
    ) -> WorkflowStep:
        async with self.uow:
            step = await self._update_step_component(step_id, component_id, actor_id)
            await self.uow.commit()
        return step

    async def _update_step_component(
        self, step_id: uuid.UUID, component_id: uuid.UUID | None, actor_id: uuid.UUID
    ) -> WorkflowStep:
        step, workflow = await self.get_step_with_workflow(step_id)
        self._require_steps_editable(workflow)
        if step.match_status == StepMatchStatus.INLINE:
            raise InlineStepNotBindableError(step_id)

        if component_id is not None:
            # a tool, or - nested - another workflow, as long as that one does not
            # (eventually) run this workflow itself
            child = await self.uow.components.find_by_id(component_id)
            if child is None:
                raise ComponentNotFoundError(component_id)
            self._require_bindable(child, actor_id)
            await self._require_acyclic(workflow, [child.id])
            lifecycle.bind_step(step, child)
        else:
            lifecycle.unbind_step(step)

        return await self.uow.workflows.add_step(step)

    async def _confirm_step(self, step_id: uuid.UUID) -> WorkflowStep:
        step, workflow = await self.get_step_with_workflow(step_id)
        self._require_steps_editable(workflow)
        if step.component_id is None:
            raise WorkflowStepNotMatchedError(step_id)

        lifecycle.confirm_step(step)
        return await self.uow.workflows.add_step(step)

    @staticmethod
    def _require_bindable(child: Component, actor_id: uuid.UUID) -> None:
        """A new step may only run what lifecycle.can_bind allows. Someone else's draft is
        reported as not found, exactly like an unknown id - its existence is private."""
        if lifecycle.can_bind(child, actor_id):
            return
        if lifecycle.is_deprecated(child):
            raise ComponentDeprecatedError(f"{child.name} v{child.version}", child.deprecation_note)
        raise ComponentNotFoundError(child.id)

    @staticmethod
    def _require_steps_editable(workflow: Component) -> None:
        if lifecycle.edited_in_builder(workflow):
            raise StepsEditedInBuilderError(workflow.id)
        # a version that was ever public is what others saw, nested or downloaded - rebinding
        # a step would silently change it under them, so a change goes into the next version
        if not lifecycle.steps_editable(workflow):
            raise PublishedWorkflowStepsLockedError(workflow.id)

    async def execute_step_command(self, step: WorkflowStep, command: WorkflowStepCommand) -> WorkflowStep:
        async with self.uow:
            match command.type:
                case WorkflowStepCommandType.CONFIRM:
                    step = await self._confirm_step(step.id)
            await self.uow.commit()
        return step

    #: plausible $import/$include targets - all text, so an unrelated binary in the archive
    #: never has to be decoded just to be ignored
    _AUX_EXTENSIONS = (".yml", ".yaml", ".json")

    @staticmethod
    def _files_for(cwl_content: str, auxiliary: dict[str, str]) -> list[ComponentFile]:
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
        return [ComponentFile(path=path, content=content) for path, content in sorted(needed.items())]

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
            match = match_archive_path(target, aux_files)
            if match is None:
                missing.add(target)
                continue
            content = aux_files[match]
            resolved[target] = content
            pending.extend(collect_import_targets(content))

        return resolved, sorted(missing)

    def _extract_zip_files(self, zip_bytes: bytes) -> dict[str, str]:
        """The archive's .cwl documents, keyed by path relative to the archive root - a
        `run:` resolves relative to the document that writes it, so `cwl/inner.cwl` running
        `tool.cwl` needs to know it means `cwl/tool.cwl`. A single wrapper folder (what
        Finder adds when you zip a directory) is stripped, as in _extract_zip_aux_files."""
        try:
            with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
                bad_file = zf.testzip()
                if bad_file is not None:
                    raise InvalidWorkflowArchiveError(f"Corrupt file in archive: {bad_file}")
                # skip macOS AppleDouble sidecar files (e.g. "._pipeline.cwl") and the
                # __MACOSX/ dir Finder adds automatically when zipping - these mirror real
                # filenames but hold binary resource-fork data, not CWL content
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
                    if not name.lower().endswith(".cwl"):
                        continue
                    path = name[len(prefix) :] if prefix and name.startswith(prefix) else name
                    try:
                        result[path] = zf.read(name).decode("utf-8")
                    except UnicodeDecodeError as err:
                        raise InvalidWorkflowArchiveError(f"'{path}' is not valid UTF-8 text") from err
                if not result:
                    raise InvalidWorkflowArchiveError("Archive contains no .cwl files")
                return result
        except zipfile.BadZipFile as err:
            raise InvalidWorkflowArchiveError("Not a valid zip archive") from err
