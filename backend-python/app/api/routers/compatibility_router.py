from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dto.compatibility import CompatibilityRequestDto, CompatibilityResponseDto, FormatPairResultDto
from app.application.service.compatibility_service import CompatibilityService, FormatPair

router = APIRouter(prefix="/compatibility", tags=["compatibility"])


@router.post("", response_model=CompatibilityResponseDto)
async def check_compatibility(
    dto: CompatibilityRequestDto,
    compatibility_service: Annotated[CompatibilityService, Depends(CompatibilityService.get_service)],
) -> CompatibilityResponseDto:
    """Which output formats may feed which input formats - the workflow builder's
    format-aware type check, proxied to the SOS File Format Service. Batched, because the
    builder ranks its whole palette against the canvas at once."""
    pairs = [
        FormatPair(actual_format=p.actual_format, expected_format=p.expected_format, ontology_url=p.ontology_url)
        for p in dto.pairs
    ]
    results = await compatibility_service.check_pairs(pairs)
    return CompatibilityResponseDto(
        results=[
            FormatPairResultDto(
                actual_format=r.pair.actual_format,
                expected_format=r.pair.expected_format,
                ontology_url=r.pair.ontology_url,
                compatible=r.compatible,
            )
            for r in results
        ]
    )
