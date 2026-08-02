import io
import uuid
import zipfile

from fastapi import Depends

from app.domain.exception.component_exceptions import ComponentNotFoundError
from app.domain.models.component import Component
from app.domain.repository.components_repository import ComponentsRepository
from app.infrastructure.cwl.cwl_parser import generate_inputs_yaml, inject_description


class ComponentsService:
    def __init__(self, components_repository: ComponentsRepository):
        self.components_repository = components_repository

    @staticmethod
    def get_service(
        components_repository: ComponentsRepository = Depends(ComponentsRepository.get_repository),
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