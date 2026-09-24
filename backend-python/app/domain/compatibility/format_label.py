from enum import StrEnum

from app.domain.models.parameter import Parameter


class FormatLabelSource(StrEnum):
    #: resolved from the component's ontology by the format service
    ONTOLOGY = "ontology"
    #: written by hand for a port no ontology covers (e.g. "RDS") - display only
    MANUAL = "manual"
    #: an ontology format whose label could not be resolved (yet)
    UNRESOLVED = "unresolved"


def has_ontology_format(parameter: Parameter, ontology_url: str | None) -> bool:
    """Only a namespaced format expands to a URI - a bare token like `rds` never is one."""
    return parameter.format is not None and "://" in parameter.format and ontology_url is not None


def accepts_manual_format_label(parameter: Parameter, ontology_url: str | None) -> bool:
    """Whether a port's label is the user's to write: a File port whose format no ontology
    resolves - none at all, or a bare token like `rds`. An ontology-resolved label is never
    overwritten by hand."""
    is_file = parameter.cwl_type.strip().lower().startswith("file")
    return is_file and not has_ontology_format(parameter, ontology_url)


def format_label_source(parameter: Parameter, ontology_url: str | None) -> FormatLabelSource | None:
    """Where a parameter's label comes from - None when it has neither label nor ontology format."""
    if has_ontology_format(parameter, ontology_url):
        return FormatLabelSource.ONTOLOGY if parameter.format_label else FormatLabelSource.UNRESOLVED
    if parameter.format_label and accepts_manual_format_label(parameter, ontology_url):
        return FormatLabelSource.MANUAL
    return None
