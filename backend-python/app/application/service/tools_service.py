import io
import uuid
import zipfile
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.application.commands.commands import ManualFormatLabel, ToolCommand, ToolCommandType
from app.application.exception.component_exceptions import (
    AlreadyPackagedError,
    ComponentKindMismatchError,
    InvalidCwlError,
    ManualUploadCannotBeRepackagedError,
    MissingCommandPayloadError,
    PackagedCommitChangedError,
)
from app.application.service.components_service import ComponentsService
from app.domain.compatibility.format_label import accepts_manual_format_label
from app.domain.models.component import Component, ComponentKind, ComponentSource
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.parameter import Parameter
from app.domain.models.tool import Tool
from app.domain.repository.components_repository import ComponentsRepository
from app.infrastructure.cwl.cwl_parser import (
    extract_cwl_type,
    extract_description,
    extract_docker_pull,
    extract_dockerfile_content,
    generate_inputs_yaml,
    inject_description,
)
from app.infrastructure.packaging.packaging_service_client import PackagingServiceClient

#: the CWL classes a tool may be - the leaves of the composite
TOOL_CWL_CLASSES = {"CommandLineTool", "ExpressionTool"}


@dataclass
class ParsedTool:
    """A .cwl read but not persisted - see ToolsService.parse_cwl."""

    cwl_content: str
    cwl_type: str | None
    description: str | None
    dockerfile_content: str | None
    docker_pull_reference: str | None
    ontology_url: str | None
    parameters: list[Parameter]


@dataclass
class PackagePreview:
    """A GitHub repo packaged but not persisted - see ToolsService.preview_package."""

    parsed: ParsedTool
    repo_name: str
    repo_url: str
    commit_sha: str
    author: str | None
    #: latest version of the lineage already packaged from this repo, if any
    existing: Component | None
    #: the repo's current commit is exactly what `existing` was packaged from
    already_packaged: bool


class ToolsService:
    """What only a tool - the leaf of the composite - does: being uploaded as a single
    CWL document or packaged from a repository, carrying a container, and hand-labelled
    format ports. Everything shared with workflows is ComponentsService's."""

    def __init__(
        self,
        components_repository: ComponentsRepository,
        components_service: ComponentsService,
        packaging_client: PackagingServiceClient,
    ):
        self.components_repository = components_repository
        self.components_service = components_service
        self.packaging_client = packaging_client

    @staticmethod
    def get_service(
        components_repository: Annotated[ComponentsRepository, Depends(ComponentsRepository.get_repository)],
        components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
        packaging_client: Annotated[PackagingServiceClient, Depends(PackagingServiceClient.get_client)],
    ) -> "ToolsService":
        return ToolsService(components_repository, components_service, packaging_client)

    async def get_bundle(self, tool: Component) -> tuple[str, bytes]:
        base_name = f"{tool.name}-v{tool.version}"
        cwl_content = inject_description(tool.cwl_content, tool.description)
        inputs_yaml = generate_inputs_yaml(tool.parameters, tool.name, tool.version)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{base_name}.cwl", cwl_content)
            zf.writestr("inputs.yaml", inputs_yaml)
            for file in sorted(tool.files, key=lambda f: f.path):
                zf.writestr(file.path, file.content)

        return f"{base_name}.zip", buffer.getvalue()

    async def parse_cwl(self, content: bytes) -> ParsedTool:
        """Read an uploaded .cwl into everything the UI needs to preview it, without
        persisting anything - the tool-side counterpart of
        WorkflowsService.parse_workflow_upload, so a tool can be reviewed before it is
        created rather than only after.

        Uses exactly the extractors create_manual uses, so the preview is what gets saved.
        """
        try:
            cwl_content = content.decode("utf-8")
        except UnicodeDecodeError as err:
            raise InvalidCwlError("Uploaded", "File is not valid UTF-8 text") from err
        return await self._build_preview(cwl_content, "Uploaded", ComponentSource.MANUAL_UPLOAD)

    async def preview_package(self, repo_url: str) -> PackagePreview:
        """Package a GitHub repo without persisting it, so the generated tool can be
        reviewed (and its File ports labelled) before it is created - the packaging
        counterpart of parse_cwl.

        For a repo that's already packaged, the preview carries the latest version's hand
        labels forward, exactly like add_manual_version does on save.
        """
        repo_name, cwl_content, commit_sha, description, author = await self._run_packaging(repo_url)
        parsed = await self._build_preview(cwl_content, "CLI-generated", ComponentSource.AUTOMATED_PACKAGING)
        if parsed.description is None:
            parsed.description = self.components_service.truncate_description(description)

        existing = await self.find_tool_by_repo_url(repo_url)
        latest = (
            await self.components_service.find_latest_version_by_name(existing.name) if existing is not None else None
        )
        if latest is not None:
            self._apply_manual_format_labels_to(
                parsed.parameters, parsed.ontology_url, self._manual_format_labels_of(latest)
            )
        return PackagePreview(
            parsed=parsed,
            repo_name=repo_name,
            repo_url=repo_url,
            commit_sha=commit_sha,
            author=author,
            existing=latest,
            already_packaged=latest is not None and bool(commit_sha) and latest.repo_commit_sha == commit_sha,
        )

    async def _build_preview(self, cwl_content: str, context: str, source: ComponentSource) -> ParsedTool:
        # source matters: parse_ports drops formats for packaged tools, so the preview
        # must use the same source the tool will be saved with
        cwl_type = self._require_tool_class(cwl_content, context)
        parameters = self.components_service.parse_ports(cwl_content, context, source)
        ontology_url = self.components_service.ontology_url_for(cwl_content)
        await self.components_service.resolve_format_labels(ontology_url, parameters)
        return ParsedTool(
            cwl_content=cwl_content,
            cwl_type=cwl_type,
            description=extract_description(cwl_content),
            dockerfile_content=extract_dockerfile_content(cwl_content),
            docker_pull_reference=extract_docker_pull(cwl_content),
            ontology_url=ontology_url,
            parameters=parameters,
        )

    @staticmethod
    def _require_tool_class(cwl_content: str, context: str) -> str | None:
        """The document's CWL class - which must be one a tool can be. A `class: Workflow`
        is a composite and has to come in through the workflow upload instead."""
        cwl_type = extract_cwl_type(cwl_content)
        if cwl_type is not None and cwl_type not in TOOL_CWL_CLASSES:
            raise InvalidCwlError(
                context,
                f"a {cwl_type} is not a tool (expected one of {', '.join(sorted(TOOL_CWL_CLASSES))})"
                + (" - upload it as a workflow instead" if cwl_type == "Workflow" else ""),
            )
        return cwl_type

    async def _prepare(self, tool: Component, context: str) -> None:
        """Everything derived from a tool's CWL, filled in on `tool` before it is saved."""
        tool.kind = ComponentKind.TOOL
        cwl_type = self._require_tool_class(tool.cwl_content, context)
        await self.components_service.assign_ports(tool, context)
        tool.tool = Tool(
            cwl_type=cwl_type,
            dockerfile_content=extract_dockerfile_content(tool.cwl_content),
            docker_pull_reference=extract_docker_pull(tool.cwl_content),
        )
        if tool.description is None:
            tool.description = extract_description(tool.cwl_content)
        tool.description = self.components_service.truncate_description(tool.description)

    async def create_manual(
        self,
        tool: Component,
        context: str = "Uploaded",
        format_labels: list[ManualFormatLabel] | None = None,
    ) -> Component:
        await self.components_service.require_name_available(tool.name, "add a new version instead of creating a new component")
        await self._prepare(tool, context)
        self._apply_manual_format_labels(tool, format_labels or [])
        return await self.components_service.save_and_reload(tool)

    async def add_manual_version(
        self, tool: Component, format_labels: list[ManualFormatLabel] | None = None
    ) -> Component:
        versions = await self.components_repository.find_versions_by_name(tool.name)
        if versions and not versions[-1].is_tool:
            raise ComponentKindMismatchError(tool.name, ComponentKind(versions[-1].kind).value)
        next_version = versions[-1].version + 1 if versions else 1

        tool.version = next_version
        await self._prepare(tool, f"v{next_version}")
        if versions:
            # hand labels live outside the CWL, so a new version (e.g. a MoveApps repo
            # re-packaged from GitHub) would otherwise silently lose them
            self._apply_manual_format_labels(tool, self._manual_format_labels_of(versions[-1]))
        # applied after the carried-over ones, so a reviewed label overrides (or clears) them
        self._apply_manual_format_labels(tool, format_labels or [])
        return await self.components_service.save_and_reload(tool)

    async def find_tool_by_repo_url(self, repo_url: str) -> Component | None:
        return await self.components_repository.find_tool_by_repo_url(repo_url)

    async def create_from_url(
        self,
        repo_url: str,
        domains: list[str],
        description_override: str | None,
        created_by_id: uuid.UUID,
        name: str | None = None,
        format_labels: list[ManualFormatLabel] | None = None,
        expected_commit_sha: str | None = None,
    ) -> Component:
        repo_name, cwl_content, commit_sha, metadata_description, metadata_author = await self._run_packaging(repo_url)
        self._check_expected_commit(repo_name, commit_sha, expected_commit_sha)

        tool = Component(
            kind=ComponentKind.TOOL,
            name=(name or "").strip() or repo_name,
            author_name=metadata_author,
            created_by_id=created_by_id,
            repo_url=repo_url,
            repo_commit_sha=commit_sha,
            version=1,
            cwl_content=cwl_content,
            description=description_override if description_override is not None else metadata_description,
            source=ComponentSource.AUTOMATED_PACKAGING,
            domains=[ComponentDomain(domain=d) for d in domains],
        )
        return await self.create_manual(tool, context="CLI-generated", format_labels=format_labels)

    async def package_next_version(
        self,
        existing: Component,
        description_override: str | None,
        format_labels: list[ManualFormatLabel] | None = None,
        expected_commit_sha: str | None = None,
    ) -> Component:
        repo_name, cwl_content, commit_sha, metadata_description, _ = await self._run_packaging(existing.repo_url)
        self._check_expected_commit(repo_name, commit_sha, expected_commit_sha)

        if commit_sha and existing.repo_commit_sha == commit_sha:
            raise AlreadyPackagedError(repo_name, commit_sha)

        tool = Component(
            kind=ComponentKind.TOOL,
            name=existing.name,
            author_name=existing.author_name,
            created_by_id=existing.created_by_id,
            repo_url=existing.repo_url,
            repo_commit_sha=commit_sha,
            cwl_content=cwl_content,
            description=description_override if description_override is not None else metadata_description,
            source=existing.source,
            domains=[ComponentDomain(domain=d.domain) for d in existing.domains],
        )
        return await self.add_manual_version(tool, format_labels)

    @staticmethod
    def _check_expected_commit(repo_name: str, commit_sha: str | None, expected_commit_sha: str | None) -> None:
        # packaging runs again on create - if the repo moved on since the preview, the
        # user would otherwise save a CWL (and label ports) they never reviewed
        if expected_commit_sha is not None and commit_sha != expected_commit_sha:
            raise PackagedCommitChangedError(repo_name, expected_commit_sha, commit_sha)

    async def repackage(self, parent: Component) -> Component:
        if parent.repo_url is None:
            raise ManualUploadCannotBeRepackagedError()

        versions = await self.components_repository.find_versions_by_name(parent.name)
        latest = versions[-1] if versions else None

        repo_name, cwl_content, commit_sha, metadata_description, _ = await self._run_packaging(parent.repo_url)

        if commit_sha and latest is not None and latest.repo_commit_sha == commit_sha:
            raise AlreadyPackagedError(repo_name, commit_sha)

        tool = Component(
            kind=ComponentKind.TOOL,
            name=parent.name,
            author_name=parent.author_name,
            created_by_id=parent.created_by_id,
            repo_url=parent.repo_url,
            repo_commit_sha=commit_sha,
            cwl_content=cwl_content,
            description=metadata_description,
            source=parent.source,
            domains=[ComponentDomain(domain=d.domain) for d in parent.domains],
        )
        return await self.add_manual_version(tool)

    async def execute_command(self, tool: Component, command: ToolCommand) -> Component:
        match command.type:
            case ToolCommandType.REPACKAGE:
                return await self.repackage(tool)
            case ToolCommandType.UPDATE_FORMAT_LABELS:
                return await self.update_format_labels(tool, command.format_labels)

    async def _run_packaging(self, repo_url: str) -> tuple[str, str, str | None, str | None, str | None]:
        result = await self.packaging_client.package(repo_url)
        return result.repo_name, result.cwl, result.commit_sha, result.description, result.author

    async def update_format_labels(self, tool: Component, format_labels: list[ManualFormatLabel] | None) -> Component:
        if format_labels is None:
            raise MissingCommandPayloadError(ToolCommandType.UPDATE_FORMAT_LABELS, "formatLabels")
        self._apply_manual_format_labels(tool, format_labels)
        return await self.components_service.save_and_reload(tool)

    def _apply_manual_format_labels(self, tool: Component, format_labels: list[ManualFormatLabel]) -> None:
        self._apply_manual_format_labels_to(tool.parameters, tool.ontology_url, format_labels)

    @staticmethod
    def _apply_manual_format_labels_to(
        parameters: list[Parameter], ontology_url: str | None, format_labels: list[ManualFormatLabel]
    ) -> None:
        by_port = {(label.name, label.direction): label for label in format_labels}
        for parameter in parameters:
            label = by_port.get((parameter.name, parameter.direction))
            if label is None or not accepts_manual_format_label(parameter, ontology_url):
                continue
            parameter.format_label = (label.label or "").strip() or None

    def _manual_format_labels_of(self, tool: Component) -> list[ManualFormatLabel]:
        return [
            ManualFormatLabel(name=p.name, direction=p.direction, label=p.format_label)
            for p in tool.parameters
            if p.format_label and accepts_manual_format_label(p, tool.ontology_url)
        ]
