from app.domain.compatibility.format_label import (
    FormatLabelSource,
    accepts_manual_format_label,
    format_label_source,
)
from app.domain.models.parameter import Parameter, ParameterDirection

EDAM = "http://ontology/edam_eo.owl"
BAM = "http://edamontology.org/format_2572"


def parameter(cwl_type: str = "File", format: str | None = None, format_label: str | None = None) -> Parameter:
    return Parameter(
        name="p", cwl_type=cwl_type, format=format, format_label=format_label, direction=ParameterDirection.INPUT
    )


class TestAcceptsManualLabel:
    def test_file_port_without_format(self) -> None:
        assert accepts_manual_format_label(parameter(), EDAM)

    def test_bare_format_token_even_with_an_ontology(self) -> None:
        assert accepts_manual_format_label(parameter(format="rds"), EDAM)

    def test_not_an_ontology_format(self) -> None:
        assert not accepts_manual_format_label(parameter(format=BAM, format_label="BAM"), EDAM)

    def test_uri_format_without_ontology_is_labelable(self) -> None:
        # a namespaced format in a CWL without $schemas - nothing can resolve it
        assert accepts_manual_format_label(parameter(format=BAM), None)

    def test_not_a_config_parameter(self) -> None:
        assert not accepts_manual_format_label(parameter(cwl_type="double"), None)


class TestFormatLabelSource:
    def test_manual(self) -> None:
        assert format_label_source(parameter(format_label="RDS"), None) == FormatLabelSource.MANUAL
        assert format_label_source(parameter(format="rds", format_label="RDS"), EDAM) == FormatLabelSource.MANUAL

    def test_ontology(self) -> None:
        assert format_label_source(parameter(format=BAM, format_label="BAM"), EDAM) == FormatLabelSource.ONTOLOGY

    def test_unresolved_ontology_format(self) -> None:
        assert format_label_source(parameter(format=BAM), EDAM) == FormatLabelSource.UNRESOLVED

    def test_nothing(self) -> None:
        assert format_label_source(parameter(), None) is None
        assert format_label_source(parameter(format="rds"), None) is None
