from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dto.stats import StatsDto
from app.application.service.components_service import ComponentsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsDto)
async def get_stats(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> StatsDto:
    components_published, contributors = await components_service.get_stats()
    return StatsDto(
        components_published=components_published,
        # hardcoded: there's no workflow concept anywhere in this backend yet (no model,
        # no table, no endpoints) - real zero rather than fabricating a number
        workflows_composed=0,
        contributors=contributors,
    )
