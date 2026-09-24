from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dto.compatibility import CompatibilityRequestDto, CompatibilityResponseDto, ConnectionCheckDto
from app.application.service.auth_service import AuthService
from app.application.service.compatibility_service import CompatibilityService, Connection
from app.domain.models.user import User

router = APIRouter(prefix="/compatibility", tags=["compatibility"])


@router.post("", response_model=CompatibilityResponseDto)
async def check_connections(
    dto: CompatibilityRequestDto,
    compatibility_service: Annotated[CompatibilityService, Depends(CompatibilityService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> CompatibilityResponseDto:
    """Whether each workflow-builder connection is compatible, incompatible or unverified -
    and why. Batched: the builder checks every edge of a canvas in one request."""
    connections = [
        Connection(
            source_component_id=c.source_component_id,
            source_port=c.source_port,
            target_component_id=c.target_component_id,
            target_port=c.target_port,
        )
        for c in dto.connections
    ]
    checks = await compatibility_service.check_connections(connections, current_user)
    return CompatibilityResponseDto(
        results=[ConnectionCheckDto(status=c.status, reason=c.reason, message=c.message) for c in checks]
    )
