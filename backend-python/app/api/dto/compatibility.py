from pydantic import Field

from app.api.dto.base import CamelModel

MAX_COMPATIBILITY_PAIRS = 200


class FormatPairDto(CamelModel):
    #: the output port's format
    actual_format: str
    #: the input port's format
    expected_format: str
    #: both ports' ontology (Component.ontology_url) - pairs across ontologies can't be checked
    ontology_url: str


class CompatibilityRequestDto(CamelModel):
    pairs: list[FormatPairDto] = Field(max_length=MAX_COMPATIBILITY_PAIRS)


class FormatPairResultDto(FormatPairDto):
    #: null when the pair couldn't be checked (format service unavailable, or an ontology
    #: no component uses) - the builder treats that as an unverified connection
    compatible: bool | None


class CompatibilityResponseDto(CamelModel):
    #: one per requested pair, in request order
    results: list[FormatPairResultDto]
