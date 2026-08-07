import uuid
from typing import Annotated

from fastapi import Depends

from app.application.service.components_service import ComponentsService
from app.domain.repository.favorites_repository import FavoritesRepository


class FavoritesService:
    def __init__(self, favorites_repository: FavoritesRepository, components_service: ComponentsService):
        self.favorites_repository = favorites_repository
        self.components_service = components_service

    @staticmethod
    def get_service(
        favorites_repository: Annotated[FavoritesRepository, Depends(FavoritesRepository.get_repository)],
        components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    ) -> "FavoritesService":
        return FavoritesService(favorites_repository, components_service)

    async def add_favorite(self, user_id: uuid.UUID, component_id: uuid.UUID) -> None:
        # favoriting is scoped to the whole lineage (name), not the specific version row
        # the star was clicked on - so every version of the same component favorites together
        component = await self.components_service.get_component(component_id)
        await self.favorites_repository.add(user_id, component.name)

    async def remove_favorite(self, user_id: uuid.UUID, component_id: uuid.UUID) -> None:
        component = await self.components_service.get_component(component_id)
        await self.favorites_repository.remove(user_id, component.name)

    async def get_favorited_component_names(self, user_id: uuid.UUID) -> set[str]:
        return await self.favorites_repository.find_favorited_component_names(user_id)