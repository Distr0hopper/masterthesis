import uuid

from fastapi import Depends

from app.domain.exception.component_exceptions import ComponentNotFoundError
from app.domain.models.component import Component
from app.domain.repository.components_repository import ComponentsRepository


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