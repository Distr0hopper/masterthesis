import io
import subprocess
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from app.application.exception.component_exceptions import (
    AlreadyPackagedError,
    ComponentNameAlreadyExistsError,
    ComponentNotFoundError,
    InvalidCwlError,
    ManualUploadCannotBeRepackagedError,
    PackagingFailedError,
)
from app.domain.models.component import Component, ComponentSource
from app.domain.models.parameter import Parameter
from app.domain.repository.components_repository import ComponentsRepository
from app.infrastructure.cwl.cwl_parser import (
    extract_cwl_type,
    extract_description,
    extract_dockerfile_content,
    extract_parameters,
    generate_inputs_yaml,
    inject_description,
)
from app.infrastructure.packaging.packaging_cli import read_packaging_output, run_packaging_cli


class ComponentsService:
    def __init__(self, components_repository: ComponentsRepository):
        self.components_repository = components_repository

    @staticmethod
    def get_service(
        components_repository: Annotated[ComponentsRepository, Depends(ComponentsRepository.get_repository)],
    ) -> "ComponentsService":
        return ComponentsService(components_repository)

    async def list_components(self, domain: str | None = None) -> list[Component]:
        return await self.components_repository.find_all(domain)

    async def get_component(self, component_id: uuid.UUID) -> Component:
        component = await self.components_repository.find_by_id(component_id)
        if component is None:
            raise ComponentNotFoundError(component_id)
        return component

    async def get_versions(self, component: Component) -> list[Component]:
        return await self.components_repository.find_versions_by_name(component.name)

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

        return f"{base_name}.zip", buffer.getvalue()

    async def create_manual(self, component: Component, context: str = "Uploaded") -> Component:
        # a brand new component always starts at version 1 - if a component with this name
        # already exists (at any version), that insert would otherwise fail on the DB's
        # unique (name, version) constraint instead of a handled error
        existing_versions = await self.components_repository.find_versions_by_name(component.name)
        if existing_versions:
            raise ComponentNameAlreadyExistsError(component.name)

        component.parameters = self._parse_parameters(component.cwl_content, context, component.source)
        component.cwl_type = extract_cwl_type(component.cwl_content)
        component.dockerfile_content = extract_dockerfile_content(component.cwl_content)
        if component.description is None:
            component.description = extract_description(component.cwl_content)

        return await self._save_and_reload(component)

    async def add_manual_version(self, component: Component) -> Component:
        versions = await self.components_repository.find_versions_by_name(component.name)
        next_version = versions[-1].version + 1 if versions else 1

        component.version = next_version
        component.parameters = self._parse_parameters(component.cwl_content, f"v{next_version}", component.source)
        component.cwl_type = extract_cwl_type(component.cwl_content)
        component.dockerfile_content = extract_dockerfile_content(component.cwl_content)
        if component.description is None:
            component.description = extract_description(component.cwl_content)

        return await self._save_and_reload(component)

    async def find_component_by_repo_url(self, repo_url: str) -> Component | None:
        return await self.components_repository.find_by_repo_url(repo_url)

    async def create_from_url(
        self,
        repo_url: str,
        domain: str,
        description_override: str | None,
        created_by_id: uuid.UUID,
    ) -> Component:
        repo_name, cwl_content, commit_sha, metadata_description, metadata_author = await self._run_packaging(repo_url)

        component = Component(
            name=repo_name,
            author_name=metadata_author,
            created_by_id=created_by_id,
            repo_url=repo_url,
            repo_commit_sha=commit_sha,
            version=1,
            cwl_content=cwl_content,
            description=description_override if description_override is not None else metadata_description,
            source=ComponentSource.AUTOMATED_PACKAGING,
            domain=domain,
        )
        return await self.create_manual(component, context="CLI-generated")

    async def package_next_version(self, existing: Component, description_override: str | None) -> Component:
        repo_name, cwl_content, commit_sha, metadata_description, _ = await self._run_packaging(existing.repo_url)

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
            domain=existing.domain,
        )
        return await self.add_manual_version(component)

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
            domain=parent.domain,
        )
        return await self.add_manual_version(component)

    async def _run_packaging(self, repo_url: str) -> tuple[str, str, str | None, str | None, str | None]:
        repo_name = repo_url.rstrip("/").split("/")[-1]
        with tempfile.TemporaryDirectory(prefix="moveapps-") as tmp:
            output_dir = Path(tmp)
            try:
                await run_packaging_cli(repo_url, output_dir)
            except subprocess.CalledProcessError as err:
                reason = err.stderr.decode().strip() if err.stderr else f"exit code {err.returncode}"
                raise PackagingFailedError(repo_name, reason) from err
            cwl_content, commit_sha, description, author = read_packaging_output(output_dir, repo_name)
        return repo_name, cwl_content, commit_sha, description, author

    async def update_component(self, component: Component) -> Component:
        return await self._save_and_reload(component)

    async def remove(self, component: Component) -> None:
        await self.components_repository.delete(component)

    async def _save_and_reload(self, component: Component) -> Component:
        saved = await self.components_repository.save(component)
        # re-fetch: created_by is only guaranteed to be safely (selectin) loaded
        # via a fresh query, not by touching the just-inserted in-memory object
        reloaded = await self.components_repository.find_by_id(saved.id)
        assert reloaded is not None
        return reloaded

    def _parse_parameters(self, cwl_content: str, context: str, source: ComponentSource) -> list[Parameter]:
        try:
            parameters = extract_parameters(cwl_content)
        except ValueError as err:
            raise InvalidCwlError(context, str(err)) from err

        # format is an ontology identifier requiring a resolution step we don't run yet -
        # only trust/store it for manually uploaded components for now
        if source != ComponentSource.MANUAL_UPLOAD:
            for parameter in parameters:
                parameter.format = None
        return parameters