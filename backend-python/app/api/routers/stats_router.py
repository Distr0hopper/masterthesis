from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dto.stats import StatsDto
from app.application.service.components_service import ComponentsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsDto)
async def get_stats(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> StatsDto:
    stats = await components_service.get_stats()
    return StatsDto(
        tools_published=stats.tools_published,
        workflows_published=stats.workflows_published,
        contributors=stats.contributors,
    )
