from app.api.dto.component import FormatLabelDto, ParameterDto, PreviewParameterDto
from app.application.commands.commands import ManualFormatLabel
from app.domain.compatibility.format_label import accepts_manual_format_label, format_label_source
from app.domain.models.parameter import Parameter


class ParameterTransformer:
    """Ports, the same for every kind of component."""

    @staticmethod
    def to_parameter(parameter: Parameter, ontology_url: str | None) -> ParameterDto:
        return ParameterDto(
            id=parameter.id,
            name=parameter.name,
            cwl_type=parameter.cwl_type,
            default_value=parameter.default_value,
            description=parameter.description,
            format=parameter.format,
            format_label=parameter.format_label,
            ontology_url=ontology_url,
            format_label_source=format_label_source(parameter, ontology_url),
            accepts_manual_format_label=accepts_manual_format_label(parameter, ontology_url),
            direction=parameter.direction,
        )

    @staticmethod
    def to_preview_parameter(parameter: Parameter, id_prefix: str, ontology_url: str | None) -> PreviewParameterDto:
        return PreviewParameterDto(
            id=f"{id_prefix}:{parameter.direction.value}:{parameter.name}",
            name=parameter.name,
            cwl_type=parameter.cwl_type,
            default_value=parameter.default_value,
            description=parameter.description,
            format=parameter.format,
            format_label=parameter.format_label,
            ontology_url=ontology_url,
            format_label_source=format_label_source(parameter, ontology_url),
            accepts_manual_format_label=accepts_manual_format_label(parameter, ontology_url),
            direction=parameter.direction,
        )

    @staticmethod
    def to_format_labels(dtos: list[FormatLabelDto]) -> list[ManualFormatLabel]:
        return [ManualFormatLabel(name=d.name, direction=d.direction, label=d.label) for d in dtos]
