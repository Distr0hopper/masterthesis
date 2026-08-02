import uuid

from fastapi import APIRouter, Depends, Query

from app.api.dto.component import ComponentDetailDto, ComponentListItemDto
from app.api.transformer.component_transformer import to_detail, to_list_item
from app.application.service.components_service import ComponentsService

router = APIRouter(prefix="/components", tags=["components"])


@router.get("", response_model=list[ComponentListItemDto])
async def list_components(
    domain: str | None = Query(default=None),
    components_service: ComponentsService = Depends(ComponentsService.get_service),
) -> list[ComponentListItemDto]:
    components = await components_service.list_components(domain)
    return [to_list_item(c) for c in components]


@router.get("/{component_id}", response_model=ComponentDetailDto)
async def get_component(
    component_id: uuid.UUID,
    components_service: ComponentsService = Depends(ComponentsService.get_service),
) -> ComponentDetailDto:
    component = await components_service.get_component(component_id)
    return to_detail(component)


@router.get("/{component_id}/versions", response_model=list[ComponentListItemDto])
async def get_versions(
    component_id: uuid.UUID,
    components_service: ComponentsService = Depends(ComponentsService.get_service),
) -> list[ComponentListItemDto]:
    versions = await components_service.get_versions(component_id)
    return [to_list_item(v) for v in versions]