import uuid
from typing import Annotated

from fastapi import Depends

from app.application.service.components_service import ComponentsService
from app.application.service.workflows_service import WorkflowsService
from app.domain.models.favorite import FavoriteEntityType
from app.domain.repository.favorites_repository import FavoritesRepository


class FavoritesService:
    def __init__(
        self,
        favorites_repository: FavoritesRepository,
        components_service: ComponentsService,
        workflows_service: WorkflowsService,
    ):
        self.favorites_repository = favorites_repository
        self.components_service = components_service
        self.workflows_service = workflows_service

    @staticmethod
    def get_service(
        favorites_repository: Annotated[FavoritesRepository, Depends(FavoritesRepository.get_repository)],
        components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
        workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    ) -> "FavoritesService":
        return FavoritesService(favorites_repository, components_service, workflows_service)

    async def add_favorite(self, user_id: uuid.UUID, component_id: uuid.UUID) -> None:
        # favoriting is scoped to the whole lineage (name), not the specific version row
        # the star was clicked on - so every version of the same component favorites together
        component = await self.components_service.get_component(component_id)
        await self.favorites_repository.add(user_id, FavoriteEntityType.COMPONENT, component.name)

    async def remove_favorite(self, user_id: uuid.UUID, component_id: uuid.UUID) -> None:
        component = await self.components_service.get_component(component_id)
        await self.favorites_repository.remove(user_id, FavoriteEntityType.COMPONENT, component.name)

    async def get_favorited_component_names(self, user_id: uuid.UUID) -> set[str]:
        return await self.favorites_repository.find_favorited_refs(user_id, FavoriteEntityType.COMPONENT)

    async def remove_all_favorites(self, component_name: str) -> None:
        await self.favorites_repository.delete_by_ref(FavoriteEntityType.COMPONENT, component_name)

    async def add_workflow_favorite(self, user_id: uuid.UUID, workflow_id: uuid.UUID) -> None:
        # unlike components, workflows aren't versioned - the favorite points at the single
        # workflow row, keyed by its uuid as text
        workflow = await self.workflows_service.get_workflow(workflow_id)
        await self.favorites_repository.add(user_id, FavoriteEntityType.WORKFLOW, str(workflow.id))

    async def remove_workflow_favorite(self, user_id: uuid.UUID, workflow_id: uuid.UUID) -> None:
        workflow = await self.workflows_service.get_workflow(workflow_id)
        await self.favorites_repository.remove(user_id, FavoriteEntityType.WORKFLOW, str(workflow.id))

    async def get_favorited_workflow_ids(self, user_id: uuid.UUID) -> set[str]:
        return await self.favorites_repository.find_favorited_refs(user_id, FavoriteEntityType.WORKFLOW)

    async def remove_all_workflow_favorites(self, workflow_id: uuid.UUID) -> None:
        await self.favorites_repository.delete_by_ref(FavoriteEntityType.WORKFLOW, str(workflow_id))
