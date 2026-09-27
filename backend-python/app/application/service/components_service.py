import io
import uuid
import zipfile
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends

from app.application.commands.commands import ComponentCommand, ComponentCommandType, ManualFormatLabel
from app.application.exception.component_exceptions import (
    AlreadyPackagedError,
    ComponentNameAlreadyExistsError,
    ComponentNotFoundError,
    InvalidCwlError,
    ManualUploadCannotBeRepackagedError,
    MissingCommandPayloadError,
    PackagedCommitChangedError,
)
from app.domain.compatibility.format_label import accepts_manual_format_label
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.component import MAX_DESCRIPTION_LENGTH, Component, ComponentSource, ComponentStatus
from app.domain.models.parameter import Parameter
from app.domain.models.user import User
from app.domain.pagination.pagination import PaginatedList
from app.domain.repository.components_repository import ComponentListFilter, ComponentsRepository
from app.infrastructure.cwl.cwl_parser import (
    extract_cwl_type,
    extract_description,
    extract_docker_pull,
    extract_dockerfile_content,
    extract_parameters,
    extract_schema_url,
    generate_inputs_yaml,
    inject_description,
)
from app.infrastructure.format_service.format_service_client import FormatServiceClient
from app.infrastructure.format_service.ontology import resolve_ontology_url
from app.infrastructure.packaging.packaging_service_client import PackagingServiceClient

if TYPE_CHECKING:
    # deferred import - favorites_service.py imports ComponentsService, so importing
    # FavoritesService here at module load time would create a circular import
    from app.application.service.favorites_service import FavoritesService


@dataclass
class ParsedComponent:
    """A .cwl read but not persisted - see ComponentsService.parse_cwl."""

    cwl_content: str
    cwl_type: str | None
    description: str | None
    dockerfile_content: str | None
    docker_pull_reference: str | None
    ontology_url: str | None
    parameters: list[Parameter]


@dataclass
class PackagePreview:
    """A GitHub repo packaged but not persisted - see ComponentsService.preview_package."""

    parsed: ParsedComponent
    repo_name: str
    repo_url: str
    commit_sha: str
    author: str | None
    #: latest version of the lineage already packaged from this repo, if any
    existing: Component | None
    #: the repo's current commit is exactly what `existing` was packaged from
    already_packaged: bool


class ComponentsService:
    def __init__(
        self,
        components_repository: ComponentsRepository,
        format_service_client: FormatServiceClient,
        packaging_client: PackagingServiceClient,
    ):
        self.components_repository = components_repository
        self.format_service_client = format_service_client
        self.packaging_client = packaging_client

    @staticmethod
    def get_service(
        components_repository: Annotated[ComponentsRepository, Depends(ComponentsRepository.get_repository)],
        format_service_client: Annotated[FormatServiceClient, Depends(FormatServiceClient.get_client)],
        packaging_client: Annotated[PackagingServiceClient, Depends(PackagingServiceClient.get_client)],
    ) -> "ComponentsService":
        return ComponentsService(components_repository, format_service_client, packaging_client)

    async def list_components(
        self, filter: ComponentListFilter, pagination: PaginatedList
    ) -> tuple[list[Component], int]:
        # browse-list callers always see only PUBLISHED components
        filter = replace(filter, status=ComponentStatus.PUBLISHED, created_by=None)
        return await self.components_repository.find_paginated(filter, pagination)

    async def list_my_components_by_status(
        self, created_by_id: uuid.UUID, status: ComponentStatus, pagination: PaginatedList
    ) -> tuple[list[Component], int]:
        filter = ComponentListFilter(created_by=created_by_id, status=status)
        return await self.components_repository.find_paginated(filter, pagination)

    async def list_all_components(self, filter: ComponentListFilter) -> list[Component]:
        """Every component list_components would page through, unpaged - for callers that
        must order the whole set themselves before paging (the builder palette's ranking)."""
        filter = replace(filter, status=ComponentStatus.PUBLISHED, created_by=None)
        return await self.components_repository.find_all_filtered(filter)

    async def get_latest_components(self, limit: int) -> list[Component]:
        components = await self.components_repository.find_all(ComponentStatus.PUBLISHED)
        return sorted(components, key=lambda c: c.created_at, reverse=True)[:limit]

    async def get_stats(self) -> tuple[int, int]:
        return (
            await self.components_repository.count_distinct_names(ComponentStatus.PUBLISHED),
            await self.components_repository.count_distinct_contributors(ComponentStatus.PUBLISHED),
        )

    async def get_component(self, component_id: uuid.UUID) -> Component:
        component = await self.components_repository.find_by_id(component_id)
        if component is None:
            raise ComponentNotFoundError(component_id)
        return component

    async def get_visible_component(self, component_id: uuid.UUID, current_user: User | None) -> Component:
        component = await self.get_component(component_id)
        if not self.is_visible(component, current_user):
            raise ComponentNotFoundError(component_id)
        return component

    async def get_versions(self, component: Component) -> list[Component]:
        return await self.components_repository.find_versions_by_name(component.name)

    async def get_visible_versions(self, component: Component, current_user: User | None) -> list[Component]:
        versions = await self.get_versions(component)
        return [v for v in versions if self.is_visible(v, current_user)]

    @staticmethod
    def is_visible(component: Component, current_user: User | None) -> bool:
        if component.status == ComponentStatus.PUBLISHED:
            return True
        return current_user is not None and component.created_by_id == current_user.id

    async def get_cwl_download(self, component: Component) -> tuple[str, str]:
        filename = f"{component.name}-v{component.version}.cwl"
        content = inject_description(component.cwl_content, component.description)
        return filename, content

    async def get_bundle(self, component: Component) -> tuple[str, bytes]:
        base_name = f"{component.name}-v{component.version}"
        cwl_content = inject_description(component.cwl_content, component.description)
        inputs_yaml = generate_inputs_yaml(component.parameters, component.name, component.version)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{base_name}.cwl", cwl_content)
            zf.writestr("inputs.yaml", inputs_yaml)
            for file in sorted(component.files, key=lambda f: f.path):
                zf.writestr(file.path, file.content)

        return f"{base_name}.zip", buffer.getvalue()

    async def find_visible_latest_version_by_name(self, name: str, current_user: User | None) -> Component | None:
        """The newest version of this lineage, but only if the caller may see it.

        A name can be held by someone else's unpublished draft. The name is still taken -
        it is a global key (favourites reference components by name, and
        uq_components_name_version pins one row per name+version) - but the caller has no
        business learning anything about a draft that is not theirs, and linking them to
        a component they cannot open is a dead end.
        """
        existing = await self.find_latest_version_by_name(name)
        if existing is None or not self.is_visible(existing, current_user):
            return None
        return existing

    async def find_latest_version_by_name(self, name: str) -> Component | None:
        """The newest version of the lineage holding this exact name, if it exists.

        Backs the name-availability check the workflow-upload flow uses to resolve a
        collision before anything is written - either by renaming, or by binding the step
        to the component returned here.
        """
        versions = await self.components_repository.find_versions_by_name(name)
        return versions[-1] if versions else None

    async def parse_cwl(self, content: bytes) -> "ParsedComponent":
        """Read an uploaded .cwl into everything the UI needs to preview it, without
        persisting anything - the component-side counterpart of
        WorkflowsService.parse_workflow_upload, so a component can be reviewed before it
        is created rather than only after.

        Uses exactly the extractors create_manual uses, so the preview is what gets saved.
        """
        try:
            cwl_content = content.decode("utf-8")
        except UnicodeDecodeError as err:
            raise InvalidCwlError("Uploaded", "File is not valid UTF-8 text") from err
        return await self._build_preview(cwl_content, "Uploaded", ComponentSource.MANUAL_UPLOAD)

    async def preview_package(self, repo_url: str) -> PackagePreview:
        """Package a GitHub repo without persisting it, so the generated component can be
        reviewed (and its File ports labelled) before it is created - the packaging
        counterpart of parse_cwl.

        For a repo that's already packaged, the preview carries the latest version's hand
        labels forward, exactly like add_manual_version does on save.
        """
        repo_name, cwl_content, commit_sha, description, author = await self._run_packaging(repo_url)
        parsed = await self._build_preview(cwl_content, "CLI-generated", ComponentSource.AUTOMATED_PACKAGING)
        if parsed.description is None:
            parsed.description = self._truncate_description(description)

        existing = await self.find_component_by_repo_url(repo_url)
        latest = await self.find_latest_version_by_name(existing.name) if existing is not None else None
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

    async def _build_preview(self, cwl_content: str, context: str, source: ComponentSource) -> ParsedComponent:
        # source matters: _parse_parameters drops formats for packaged components, so the
        # preview must use the same source the component will be saved with
        parameters = self._parse_parameters(cwl_content, context, source)
        ontology_url = self.ontology_url_for(cwl_content)
        await self.resolve_format_labels(ontology_url, parameters)
        return ParsedComponent(
            cwl_content=cwl_content,
            cwl_type=extract_cwl_type(cwl_content),
            description=extract_description(cwl_content),
            dockerfile_content=extract_dockerfile_content(cwl_content),
            docker_pull_reference=extract_docker_pull(cwl_content),
            ontology_url=ontology_url,
            parameters=parameters,
        )

    async def create_manual(
        self,
        component: Component,
        context: str = "Uploaded",
        format_labels: list[ManualFormatLabel] | None = None,
    ) -> Component:
        existing_versions = await self.components_repository.find_versions_by_name(component.name)
        if existing_versions:
            raise ComponentNameAlreadyExistsError(component.name)

        component.parameters = self._parse_parameters(component.cwl_content, context, component.source)
        component.ontology_url = self.ontology_url_for(component.cwl_content)
        await self.resolve_format_labels(component.ontology_url, component.parameters)
        self._apply_manual_format_labels(component, format_labels or [])
        component.cwl_type = extract_cwl_type(component.cwl_content)
        component.dockerfile_content = extract_dockerfile_content(component.cwl_content)
        component.docker_pull_reference = extract_docker_pull(component.cwl_content)
        if component.description is None:
            component.description = extract_description(component.cwl_content)
        component.description = self._truncate_description(component.description)

        return await self._save_and_reload(component)

    async def add_manual_version(
        self, component: Component, format_labels: list[ManualFormatLabel] | None = None
    ) -> Component:
        versions = await self.components_repository.find_versions_by_name(component.name)
        next_version = versions[-1].version + 1 if versions else 1

        component.version = next_version
        component.parameters = self._parse_parameters(component.cwl_content, f"v{next_version}", component.source)
        component.ontology_url = self.ontology_url_for(component.cwl_content)
        await self.resolve_format_labels(component.ontology_url, component.parameters)
        if versions:
            # hand labels live outside the CWL, so a new version (e.g. a MoveApps repo
            # re-packaged from GitHub) would otherwise silently lose them
            self._apply_manual_format_labels(component, self._manual_format_labels_of(versions[-1]))
        # applied after the carried-over ones, so a reviewed label overrides (or clears) them
        self._apply_manual_format_labels(component, format_labels or [])
        component.cwl_type = extract_cwl_type(component.cwl_content)
        component.dockerfile_content = extract_dockerfile_content(component.cwl_content)
        component.docker_pull_reference = extract_docker_pull(component.cwl_content)
        if component.description is None:
            component.description = extract_description(component.cwl_content)
        component.description = self._truncate_description(component.description)

        return await self._save_and_reload(component)

    async def find_component_by_repo_url(self, repo_url: str) -> Component | None:
        return await self.components_repository.find_by_repo_url(repo_url)

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

        component = Component(
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
        return await self.create_manual(component, context="CLI-generated", format_labels=format_labels)

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

        component = Component(
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
        return await self.add_manual_version(component, format_labels)

    @staticmethod
    def _check_expected_commit(repo_name: str, commit_sha: str | None, expected_commit_sha: str | None) -> None:
        # packaging runs again on create - if the repo moved on since the preview, the
        # user would otherwise save a CWL (and label ports) they never reviewed
        if expected_commit_sha is not None and commit_sha != expected_commit_sha:
            raise PackagedCommitChangedError(repo_name, expected_commit_sha, commit_sha)

    async def repackage_component(self, parent: Component) -> Component:
        if parent.repo_url is None:
            raise ManualUploadCannotBeRepackagedError()

        versions = await self.components_repository.find_versions_by_name(parent.name)
        latest = versions[-1] if versions else None

        repo_name, cwl_content, commit_sha, metadata_description, _ = await self._run_packaging(parent.repo_url)

        if commit_sha and latest is not None and latest.repo_commit_sha == commit_sha:
            raise AlreadyPackagedError(repo_name, commit_sha)

        component = Component(
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
        return await self.add_manual_version(component)

    async def publish(self, component: Component) -> Component:
        if component.status == ComponentStatus.PUBLISHED:
            return component
        component.status = ComponentStatus.PUBLISHED
        return await self.components_repository.save(component)

    async def unpublish(self, component: Component) -> Component:
        if component.status == ComponentStatus.DRAFT:
            return component
        component.status = ComponentStatus.DRAFT
        return await self.components_repository.save(component)

    async def execute_command(
        self,
        component: Component,
        command: ComponentCommand,
        current_user_id: uuid.UUID,
        favorites_service: "FavoritesService",
    ) -> Component:
        match command.type:
            case ComponentCommandType.ADD_FAVORITE:
                await favorites_service.add_favorite(current_user_id, component.id)
                return component
            case ComponentCommandType.REMOVE_FAVORITE:
                await favorites_service.remove_favorite(current_user_id, component.id)
                return component
            case ComponentCommandType.REPACKAGE:
                return await self.repackage_component(component)
            case ComponentCommandType.PUBLISH:
                return await self.publish(component)
            case ComponentCommandType.UNPUBLISH:
                return await self.unpublish(component)
            case ComponentCommandType.UPDATE_DESCRIPTION:
                return await self.update_description(component, command.description)
            case ComponentCommandType.UPDATE_DOMAIN:
                return await self.update_domains(component, command.domains)
            case ComponentCommandType.UPDATE_FORMAT_LABELS:
                return await self.update_format_labels(component, command.format_labels)

    async def _run_packaging(self, repo_url: str) -> tuple[str, str, str | None, str | None, str | None]:
        result = await self.packaging_client.package(repo_url)
        return result.repo_name, result.cwl, result.commit_sha, result.description, result.author

    async def update_description(self, component: Component, description: str | None) -> Component:
        component.description = description
        return await self._save_and_reload(component)

    async def update_domains(self, component: Component, domains: list[str] | None) -> Component:
        if not domains:
            raise MissingCommandPayloadError(ComponentCommandType.UPDATE_DOMAIN, "domains")
        component.domains = [ComponentDomain(domain=d) for d in domains]
        return await self._save_and_reload(component)

    async def update_format_labels(
        self, component: Component, format_labels: list[ManualFormatLabel] | None
    ) -> Component:
        if format_labels is None:
            raise MissingCommandPayloadError(ComponentCommandType.UPDATE_FORMAT_LABELS, "formatLabels")
        self._apply_manual_format_labels(component, format_labels)
        return await self._save_and_reload(component)

    def _apply_manual_format_labels(self, component: Component, format_labels: list[ManualFormatLabel]) -> None:
        self._apply_manual_format_labels_to(component.parameters, component.ontology_url, format_labels)

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

    def _manual_format_labels_of(self, component: Component) -> list[ManualFormatLabel]:
        return [
            ManualFormatLabel(name=p.name, direction=p.direction, label=p.format_label)
            for p in component.parameters
            if p.format_label and accepts_manual_format_label(p, component.ontology_url)
        ]

    async def remove(self, component: Component) -> None:
        await self.components_repository.delete(component)

    async def _save_and_reload(self, component: Component) -> Component:
        saved = await self.components_repository.save(component)
        reloaded = await self.components_repository.find_by_id(saved.id)
        assert reloaded is not None
        return reloaded

    def _truncate_description(self, description: str | None) -> str | None:
        # explicit user-submitted descriptions are already length-validated at the DTO
        # boundary (a no-op here) - this only actually kicks in for descriptions pulled
        # from the CWL's own `doc:` field or a repo's README during packaging, neither of
        # which the user directly typed, so silently truncating beats a hard failure
        return description if description is None else description[:MAX_DESCRIPTION_LENGTH]

    def _parse_parameters(self, cwl_content: str, context: str, source: ComponentSource) -> list[Parameter]:
        try:
            parameters = extract_parameters(cwl_content)
        except ValueError as err:
            raise InvalidCwlError(context, str(err)) from err

        if source != ComponentSource.MANUAL_UPLOAD:
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
