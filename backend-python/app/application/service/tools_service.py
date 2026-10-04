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
from app.application.unit_of_work import UnitOfWork
from app.domain.compatibility.format_label import accepts_manual_format_label
from app.domain.models.component import Component, ComponentKind, ComponentSource
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.parameter import Parameter
from app.domain.models.tool import Tool
from app.infrastructure.cwl.cwl_parser import (
    extract_cwl_type,
    extract_description,
    extract_docker_pull,
    extract_dockerfile_content,
    generate_inputs_yaml,
    inject_description,
)
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.packaging.packaging_service_client import PackagingResult, PackagingServiceClient

#: the CWL classes a tool may be - the leaves of the composite
TOOL_CWL_CLASSES = {"CommandLineTool", "ExpressionTool"}


@dataclass
class ToolDetails:
    """Everything a tool derives from its CWL document - read once by
    ToolsService.read_tool_details, for the preview and for the save alike."""

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

    parsed: ToolDetails
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
    format ports. Everything shared with workflows is ComponentsService's.

    The writing methods a router calls are use cases, each opening the unit of work and
    committing once. create_tool is not: it runs inside the caller's unit of work, so
    WorkflowsService.create_from_upload can create its new tools in the same transaction
    as the workflow."""

    def __init__(
        self,
        uow: UnitOfWork,
        components_service: ComponentsService,
        packaging_client: PackagingServiceClient,
    ):
        self.uow = uow
        self.components_service = components_service
        self.packaging_client = packaging_client

    @staticmethod
    def get_service(
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
        components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
        packaging_client: Annotated[PackagingServiceClient, Depends(PackagingServiceClient.get_client)],
    ) -> "ToolsService":
        return ToolsService(uow, components_service, packaging_client)

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

    async def parse_cwl(self, content: bytes) -> ToolDetails:
        """Read an uploaded .cwl into everything the UI needs to preview it, without
        persisting anything - the tool-side counterpart of
        WorkflowsService.parse_workflow_upload, so a tool can be reviewed before it is
        created rather than only after.

        The preview is what gets saved: create_manual reads the document through the same
        read_tool_details.
        """
        try:
            cwl_content = content.decode("utf-8")
        except UnicodeDecodeError as err:
            raise InvalidCwlError("Uploaded", "File is not valid UTF-8 text") from err
        return await self.read_tool_details(cwl_content, "Uploaded", ComponentSource.MANUAL_UPLOAD)

    async def preview_package(self, repo_url: str) -> PackagePreview:
        """Package a GitHub repo without persisting it, so the generated tool can be
        reviewed (and its File ports labelled) before it is created - the packaging
        counterpart of parse_cwl.

        For a repo that's already packaged, the preview carries the latest version's hand
        labels forward, exactly like add_manual_version does on save.
        """
        result = await self.packaging_client.package(repo_url)
        # the README description, like create_from_url saves it when no override is given
        parsed = await self.read_tool_details(
            result.cwl, "CLI-generated", ComponentSource.AUTOMATED_PACKAGING, description=result.description
        )

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
            repo_name=result.repo_name,
            repo_url=repo_url,
            commit_sha=result.commit_sha,
            author=result.author,
            existing=latest,
            already_packaged=latest is not None and bool(result.commit_sha) and latest.repo_commit_sha == result.commit_sha,
        )

    async def read_tool_details(
        self, cwl_content: str, context: str, source: ComponentSource, description: str | None = None
    ) -> ToolDetails:
        """Everything a tool derives from its CWL - the only reading of it, shared by the
        previews and the save (see _prepare), so what the user reviews is what gets stored.

        `source` matters: parse_ports drops the formats of packaged tools. `description` is
        one given explicitly - by the user, or the README packaging found - and wins over
        the document's own `doc:`; either way it is cut to what the column holds.
        """
        cwl_type = self._require_tool_class(cwl_content, context)
        parameters = self.components_service.parse_ports(cwl_content, context, source)
        ontology_url = self.components_service.ontology_url_for(cwl_content)
        await self.components_service.resolve_format_labels(ontology_url, parameters)
        return ToolDetails(
            cwl_content=cwl_content,
            cwl_type=cwl_type,
            description=self.components_service.truncate_description(
                description if description is not None else extract_description(cwl_content)
            ),
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
        details = await self.read_tool_details(tool.cwl_content, context, tool.source, description=tool.description)
        tool.kind = ComponentKind.TOOL
        tool.parameters = details.parameters
        tool.ontology_url = details.ontology_url
        tool.description = details.description
        tool.tool = Tool(
            cwl_type=details.cwl_type,
            dockerfile_content=details.dockerfile_content,
            docker_pull_reference=details.docker_pull_reference,
        )

    async def create_manual(
        self,
        tool: Component,
        context: str = "Uploaded",
        format_labels: list[ManualFormatLabel] | None = None,
    ) -> Component:
        async with self.uow:
            await self.create_tool(tool, context, format_labels)
            await self.uow.commit()
        return await self.components_service.reload(tool)

    async def create_tool(
        self,
        tool: Component,
        context: str = "Uploaded",
        format_labels: list[ManualFormatLabel] | None = None,
    ) -> Component:
        """create_manual without the transaction - runs inside the caller's unit of work."""
        await self.components_service.require_name_available(tool.name, "add a new version instead of creating a new component")
        await self._prepare(tool, context)
        self._apply_manual_format_labels(tool, format_labels or [])
        return await self.uow.components.add(tool)

    async def add_manual_version(
        self, tool: Component, format_labels: list[ManualFormatLabel] | None = None
    ) -> Component:
        async with self.uow:
            await self._add_version(tool, format_labels)
            await self.uow.commit()
        return await self.components_service.reload(tool)

    async def _add_version(self, tool: Component, format_labels: list[ManualFormatLabel] | None = None) -> Component:
        versions = await self.uow.components.find_versions_by_name(tool.name)
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
        return await self.uow.components.add(tool)

    async def find_tool_by_repo_url(self, repo_url: str) -> Component | None:
        return await self.uow.components.find_tool_by_repo_url(repo_url)

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
        result = await self.packaging_client.package(repo_url)
        self._check_expected_commit(result.repo_name, result.commit_sha, expected_commit_sha)

        tool = Component(
            kind=ComponentKind.TOOL,
            name=(name or "").strip() or result.repo_name,
            author_name=result.author,
            created_by_id=created_by_id,
            repo_url=repo_url,
            repo_commit_sha=result.commit_sha,
            version=1,
            cwl_content=result.cwl,
            description=description_override if description_override is not None else result.description,
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
        """Package the repo `existing` came from again, as the next version of its lineage -
        refused when the lineage's newest version already is at the repo's current commit.

        `existing` may be any version of the lineage: the new one always builds on the
        newest (see _next_packaged_version).
        """
        if existing.repo_url is None:
            raise ManualUploadCannotBeRepackagedError()
        result = await self.packaging_client.package(existing.repo_url)
        self._check_expected_commit(result.repo_name, result.commit_sha, expected_commit_sha)

        head = (await self.uow.components.find_versions_by_name(existing.name))[-1]
        if result.commit_sha and head.repo_commit_sha == result.commit_sha:
            raise AlreadyPackagedError(result.repo_name, result.commit_sha)

        tool = self._next_packaged_version(head, result, description_override)
        return await self.add_manual_version(tool, format_labels)

    @staticmethod
    def _next_packaged_version(
        head: Component, result: PackagingResult, description_override: str | None
    ) -> Component:
        """The next version of a packaged lineage, from its newest version `head` - the
        lineage's current truth for who made it, where it lives and which domains it serves -
        and what packaging the repo returned. add_manual_version numbers it and carries the
        hand labels forward."""
        return Component(
            kind=ComponentKind.TOOL,
            name=head.name,
            author_name=head.author_name,
            created_by_id=head.created_by_id,
            repo_url=head.repo_url,
            repo_commit_sha=result.commit_sha,
            cwl_content=result.cwl,
            description=description_override if description_override is not None else result.description,
            source=head.source,
            domains=[ComponentDomain(domain=d.domain) for d in head.domains],
        )

    @staticmethod
    def _check_expected_commit(repo_name: str, commit_sha: str | None, expected_commit_sha: str | None) -> None:
        # packaging runs again on create - if the repo moved on since the preview, the
        # user would otherwise save a CWL (and label ports) they never reviewed
        if expected_commit_sha is not None and commit_sha != expected_commit_sha:
            raise PackagedCommitChangedError(repo_name, expected_commit_sha, commit_sha)

    async def repackage(self, parent: Component) -> Component:
        """The repackage command: package_next_version without an override - the README's
        description - and without a reviewed commit to hold the repo to."""
        return await self.package_next_version(parent, None)

    async def execute_command(self, tool: Component, command: ToolCommand) -> Component:
        match command.type:
            case ToolCommandType.REPACKAGE:
                return await self.repackage(tool)
            case ToolCommandType.UPDATE_FORMAT_LABELS:
                return await self.update_format_labels(tool, command.format_labels)

    async def update_format_labels(self, tool: Component, format_labels: list[ManualFormatLabel] | None) -> Component:
        if format_labels is None:
            raise MissingCommandPayloadError(ToolCommandType.UPDATE_FORMAT_LABELS, "formatLabels")
        async with self.uow:
            self._apply_manual_format_labels(tool, format_labels)
            await self.uow.components.add(tool)
            await self.uow.commit()
        return await self.components_service.reload(tool)

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
