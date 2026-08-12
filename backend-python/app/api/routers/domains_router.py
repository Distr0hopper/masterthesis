from fastapi import APIRouter

from app.api.dto.domain import DomainDto
from app.domain.models.component_domain import DOMAIN_COLORS, VALID_DOMAINS

router = APIRouter(prefix="/domains", tags=["domains"])


@router.get("", response_model=list[DomainDto])
async def list_domains() -> list[DomainDto]:
    return [DomainDto(id=domain, color=DOMAIN_COLORS[domain]) for domain in VALID_DOMAINS]
