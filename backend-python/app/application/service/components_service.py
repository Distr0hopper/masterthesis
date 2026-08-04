import io
import uuid
import zipfile
from typing import Annotated

from fastapi import Depends

from app.application.exception.component_exceptions import InvalidCwlError, NotComponentCreatorError
from app.domain.exception.component_exceptions import ComponentNotFoundError
from app.domain.models.component import Component
from app.domain.models.parameter import Parameter
from app.domain.repository.components_repository import ComponentsRepository
from app.infrastructure.cwl.cwl_parser import extract_description, extract_parameters, generate_inputs_yaml, inject_description


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

    async def get_versions(self, component_id: uuid.UUID) -> list[Component]:
        component = await self.get_component(component_id)
        return await self.components_repository.find_versions_by_name(component.name)

    async def get_cwl_download(self, component_id: uuid.UUID) -> tuple[str, str]:
        component = await self.get_component(component_id)
        filename = f"{component.name}-v{component.version}.cwl"
        content = inject_description(component.cwl_content, component.description)
        return filename, content

    async def get_bundle(self, component_id: uuid.UUID) -> tuple[str, bytes]:
        component = await self.get_component(component_id)
        base_name = f"{component.name}-v{component.version}"
        cwl_content = inject_description(component.cwl_content, component.description)
        inputs_yaml = generate_inputs_yaml(component.parameters, component.name, component.version)

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{base_name}.cwl", cwl_content)
            zf.writestr("inputs.yaml", inputs_yaml)

        return f"{base_name}.zip", buffer.getvalue()

    async def create_manual(self, component: Component) -> Component:
        component.parameters = self._parse_parameters(component.cwl_content, "Uploaded")
        if component.description is None:
            component.description = extract_description(component.cwl_content)

        return await self._save_and_reload(component)

    async def add_manual_version(
        self,
        component_id: uuid.UUID,
        cwl_content: str,
        repo_commit_sha: str | None,
        description: str | None,
        user_id: uuid.UUID,
    ) -> Component:
        parent = await self.get_component(component_id)
        if parent.created_by_id != user_id:
            raise NotComponentCreatorError()

        versions = await self.components_repository.find_versions_by_name(parent.name)
        next_version = versions[-1].version + 1 if versions else 1
        parameters = self._parse_parameters(cwl_content, f"v{next_version}")

        component = Component(
            name=parent.name,
            author_name=parent.author_name,
            created_by_id=parent.created_by_id,
            repo_url=parent.repo_url,
            repo_commit_sha=repo_commit_sha,
            version=next_version,
            cwl_content=cwl_content,
            description=description if description is not None else extract_description(cwl_content),
            source=parent.source,
            domain=parent.domain,
        )
        component.parameters = parameters

        return await self._save_and_reload(component)

    async def update_component(self, component: Component, user_id: uuid.UUID) -> Component:
        if component.created_by_id != user_id:
            raise NotComponentCreatorError()

        return await self._save_and_reload(component)

    async def remove(self, component_id: uuid.UUID, user_id: uuid.UUID) -> None:
        component = await self.get_component(component_id)
        if component.created_by_id != user_id:
            raise NotComponentCreatorError()

        await self.components_repository.delete(component)

    async def _save_and_reload(self, component: Component) -> Component:
        saved = await self.components_repository.save(component)
        # re-fetch: created_by is only guaranteed to be safely (selectin) loaded
        # via a fresh query, not by touching the just-inserted in-memory object
        reloaded = await self.components_repository.find_by_id(saved.id)
        assert reloaded is not None
        return reloaded

    def _parse_parameters(self, cwl_content: str, context: str) -> list[Parameter]:
        try:
            return extract_parameters(cwl_content)
        except ValueError as err:
            raise InvalidCwlError(context, str(err)) from err