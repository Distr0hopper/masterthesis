from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from app.domain.repository.components_repository import ComponentsRepository
from app.infrastructure.format_service.format_service_client import FormatServiceClient

#: (actual_format, expected_format, ontology_url) -> answer. Process-wide on purpose: a
#: format's place in an ontology doesn't change, so an answer is valid for every request.
#: Only definite answers are stored - a None (service down) must be retried next time.
_cache: dict[tuple[str, str, str], bool] = {}


@dataclass(frozen=True)
class FormatPair:
    """Can an output declaring `actual_format` feed an input declaring `expected_format`?"""

    actual_format: str
    expected_format: str
    ontology_url: str


@dataclass
class FormatPairResult:
    pair: FormatPair
    #: None when the pair couldn't be checked - the builder treats that as "unverified"
    compatible: bool | None


class CompatibilityService:
    def __init__(self, components_repository: ComponentsRepository, format_service_client: FormatServiceClient):
        self.components_repository = components_repository
        self.format_service_client = format_service_client

    @staticmethod
    def get_service(
        components_repository: Annotated[ComponentsRepository, Depends(ComponentsRepository.get_repository)],
        format_service_client: Annotated[FormatServiceClient, Depends(FormatServiceClient.get_client)],
    ) -> "CompatibilityService":
        return CompatibilityService(components_repository, format_service_client)

    async def check_pairs(self, pairs: list[FormatPair]) -> list[FormatPairResult]:
        answers: dict[FormatPair, bool | None] = {}
        allowed: dict[str, bool] = {}
        # sequential: the format service caches a parsed ontology only once its first
        # request completes, so concurrent misses would each download it again
        for pair in dict.fromkeys(pairs):
            if pair.ontology_url not in allowed:
                # the format service fetches whatever URL it is given - only forward the
                # ontologies components here actually use, never an arbitrary caller URL
                allowed[pair.ontology_url] = await self.components_repository.exists_ontology_url(pair.ontology_url)
            answers[pair] = await self._check(pair) if allowed[pair.ontology_url] else None
        return [FormatPairResult(pair=pair, compatible=answers[pair]) for pair in pairs]

    async def _check(self, pair: FormatPair) -> bool | None:
        if pair.actual_format == pair.expected_format:
            return True
        key = (pair.actual_format, pair.expected_format, pair.ontology_url)
        if key in _cache:
            return _cache[key]
        compatible = await self.format_service_client.check_compatibility(
            expected_format=pair.expected_format, actual_format=pair.actual_format, ontology_url=pair.ontology_url
        )
        if compatible is not None:
            _cache[key] = compatible
        return compatible
