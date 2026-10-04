import uuid
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from typing import Annotated

from fastapi import Depends

from app.application.commands.commands import ManualFormatLabel, WorkflowStepCommand, WorkflowStepCommandType
from app.application.exception.component_exceptions import ComponentDeprecatedError, ComponentNotFoundError
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
    UnconfiguredWorkflowStepError,
    WorkflowCycleError,
    WorkflowStepNotFoundError,
    WorkflowStepNotMatchedError,
)
from app.application.service.components_service import ComponentsService
from app.application.service.tools_service import ToolsService
from app.application.unit_of_work import UnitOfWork
from app.domain.composite import lifecycle
from app.domain.composite.tree import would_create_cycle
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
)
from app.infrastructure.cwl.workflow_generator import cwl_filename_for
from app.infrastructure.cwl.workflow_parser import (
    externalize_inline_steps,
    extract_inline_components,
    extract_step_definitions,
    find_workflow_file,
    is_self_contained,
    read_workflow_overview,
    strip_cwl_extension,
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


@dataclass
class ComponentConfig:
    """The user's decision for one step: reuse an existing Component, or create a new one
    from the previewed CWL with this name/domain/description."""

    step_id: str
    reuse_component_id: uuid.UUID | None = None
    name: str | None = None
    domains: list[str] | None = None
    description: str | None = None
    format_labels: list[ManualFormatLabel] = field(default_factory=list)

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
    WorkflowDraftService.sync_to_my_workflows."""

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
            description=extract_description(upload.cwl_content),
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

        # one query, reused for every archive step's fuzzy match - the latest listed version
        # of every tool lineage, since an archive's step files are tools. Listed only: a
        # deprecated version takes no new dependents, so it is never suggested
        all_components = await self.uow.components.find_all(lifecycle.LISTED_STATUSES, ComponentKind.TOOL)
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

            existing = await self.uow.components.find_latest_by_name(suggested_name)
            parameters = self._safe_extract_parameters(cwl_content)
            ontology_url = self.components_service.ontology_url_for(cwl_content)
            await self.components_service.resolve_format_labels(ontology_url, parameters)
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
                    ontology_url=ontology_url,
                    parameters=parameters,
                    name_conflict=self._to_component_match(existing, None) if existing is not None else None,
                    suggested_match=suggested_match,
                )
            )
        return previews

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
        self, step_definitions: list[tuple[str, dict]], configs: dict[str, ComponentConfig], actor_id: uuid.UUID
    ) -> None:
        """Validates every step's configuration before any Component is created.

        Reuse configs need a target the actor may bind (see _require_bindable). Create configs get the full
        treatment: a domain, a non-blank name, no duplicate name within this upload, and
        no collision with the catalogue (the user is offered the reuse branch instead).

        Not needed for atomicity - the whole upload is one transaction - but it reports
        every configuration problem as the specific error the upload form understands,
        before any CWL is processed.
        """
        seen: set[str] = set()
        for step_id, _definition in step_definitions:
            config = configs[step_id]

            if config.is_reuse:
                if config.reuse_component_id is not None:
                    component = await self.uow.components.find_by_id(config.reuse_component_id)
                    if component is None:
                        raise ComponentNotFoundError(config.reuse_component_id)
                    self._require_bindable(component, actor_id)
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
        bare .cwl, or a zip mixing both) as a real Workflow.

        Every step must carry a ComponentConfig (keyed by step_id, as previewed by
        parse_workflow_upload): either reuse_component_id, binding the step to an existing
        catalogue Component, or a name/domain/description to create a new one from that
        step's CWL. Nothing is auto-created behind the user's back and nothing is left to
        post-save fuzzy triage - an unconfigured step is an error, not a guess.

        One transaction: the new tools and the workflow are created together or not at all.
        """
        await self.components_service.require_name_available(name)
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
        await self._validate_component_configs(configurable_steps, component_configs, created_by_id)

        extracted_by_step_id = {c.step_id: c for c in extract_inline_components(upload.cwl_content)}

        # existence already guaranteed by _validate_component_configs above
        reused_components = {
            step_id: await self.uow.components.find_by_id(config.reuse_component_id)
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
        pending_components: list[tuple[WorkflowStep, Component, list[ManualFormatLabel]]] = []
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
                kind=ComponentKind.TOOL,
                name=config.name,
                domains=[ComponentDomain(domain=d) for d in (config.domains or [])],
                cwl_content=cwl_content,
                source=ComponentSource.MANUAL_UPLOAD,
                created_by_id=created_by_id,
                description=config.description or fallback_description,
                # a component stands alone in the catalogue, so it carries its own imports
                # rather than relying on the workflow it arrived with still being around
                files=self._files_for(cwl_content, auxiliary),
            )
            step = WorkflowStep(
                step_id=step_id,
                run_reference=reference,
                step_order=order,
                match_status=StepMatchStatus.CONFIRMED,
                match_score=None,
            )
            pending_components.append((step, component, config.format_labels))
            steps.append(step)

        async with self.uow:
            for step, component, format_labels in pending_components:
                created = await self.tools_service.create_tool(component, format_labels=format_labels)
                step.component_id = created.id
                step.component = created

            workflow = await self._create_workflow(
                name=name,
                description=description,
                domains=domains,
                created_by_id=created_by_id,
                pipeline_content=pipeline_content,
                steps=steps,
                source=ComponentSource.MANUAL_UPLOAD,
                files=self._files_for(pipeline_content, auxiliary),
            )
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
        newest version's CWL and steps - in place while it is still a DRAFT, or as the
        next version once it is PUBLISHED, since a published version is what other users
        see (and nest) and must not change under them. The lineage is only reused when the
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

    async def linked_workflow_ids(self, draft_ids: set[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
        """{draft_id: newest workflow version id} for the drafts synced to My Workflows."""
        workflows = await self.uow.workflows.find_all_by_draft_ids(draft_ids)
        return {w.workflow.draft_id: w.id for w in workflows if w.workflow is not None and w.workflow.draft_id}

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
        # a public workflow is what other users see and nest - rebinding a step under
        # them would silently change it; the creator unpublishes first instead
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
