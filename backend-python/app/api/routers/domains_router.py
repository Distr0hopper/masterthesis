from fastapi import APIRouter

from app.domain.models.component_domain import VALID_DOMAINS

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=list[str])
async def list_domains() -> list[str]:
    return VALID_DOMAINS