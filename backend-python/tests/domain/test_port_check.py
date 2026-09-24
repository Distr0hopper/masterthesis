import pytest

from app.domain.compatibility.port import FormatPair
from app.domain.compatibility.port_check import (
    ConnectionStatus,
    UnverifiedReason,
    check_ports,
    cwl_types_compatible,
    format_pairs_between,
)
from tests.domain.conftest import EDAM, GEOJSON, GEOPACKAGE, OTHER, SHAPEFILE, VECTOR, input_, output

COMPATIBLE, INCOMPATIBLE, UNVERIFIED = (
    ConnectionStatus.COMPATIBLE,
    ConnectionStatus.INCOMPATIBLE,
    ConnectionStatus.UNVERIFIED,
)


class TestCwlTypes:
    @pytest.mark.parametrize(("out", "inp"), [("File", "File"), ("File[]", "File[]"), ("file", " File ")])
    def test_equal_types_fit(self, out: str, inp: str) -> None:
        assert cwl_types_compatible(out, inp)

    def test_optional_marker_is_ignored(self) -> None:
        assert cwl_types_compatible("File?", "File")
        assert cwl_types_compatible("File", "File?")

    def test_array_feeds_single_file_scatter_case(self) -> None:
        assert cwl_types_compatible("File[]", "File")

    def test_single_file_does_not_feed_array(self) -> None:
        assert not cwl_types_compatible("File", "File[]")

    def test_different_types_do_not_fit(self) -> None:
        assert not cwl_types_compatible("string", "File")
        assert not cwl_types_compatible("File", "int")


class TestStructure:
    def test_file_output_feeds_file_input(self) -> None:
        assert check_ports(output(), input_()).status != INCOMPATIBLE

    def test_mismatched_arity_is_incompatible(self) -> None:
        check = check_ports(output("File"), input_("File[]"))
        assert check.status == INCOMPATIBLE
        assert check.message == "Incompatible types - File cannot feed File[]"

    def test_config_parameters_are_not_endpoints(self) -> None:
        assert check_ports(output("string"), input_("File")).status == INCOMPATIBLE
        assert check_ports(output("File"), input_("string")).status == INCOMPATIBLE

    def test_backwards_connection_is_incompatible(self) -> None:
        assert check_ports(input_(), output()).status == INCOMPATIBLE

    def test_structure_wins_over_matching_formats(self) -> None:
        check = check_ports(output("File", format=GEOJSON, ontology_url=EDAM), input_("File[]", format=GEOJSON))
        assert check.status == INCOMPATIBLE


class TestFormats:
    def test_input_without_format_is_unverified_not_compatible(self) -> None:
        # e.g. an .rds input: no ontology covers it, so a GeoJSON output only *might* fit
        check = check_ports(output(format=GEOJSON, ontology_url=EDAM), input_())
        assert (check.status, check.reason) == (UNVERIFIED, UnverifiedReason.MISSING_INPUT_FORMAT)
        assert check.message

    def test_neither_format_is_unverified(self) -> None:
        check = check_ports(output(), input_())
        assert (check.status, check.reason) == (UNVERIFIED, UnverifiedReason.MISSING_FORMATS)

    def test_output_without_format_is_unverified(self) -> None:
        check = check_ports(output(), input_(format=VECTOR, ontology_url=EDAM))
        assert (check.status, check.reason) == (UNVERIFIED, UnverifiedReason.MISSING_OUTPUT_FORMAT)

    def test_different_ontologies_are_unverified(self, service) -> None:
        check = check_ports(output(format=GEOJSON, ontology_url=EDAM), input_(format=VECTOR, ontology_url=OTHER), service)
        assert check.reason == UnverifiedReason.DIFFERENT_ONTOLOGY

    def test_format_without_ontology_is_unverified(self, service) -> None:
        # e.g. `format: rds` in a CWL without $schemas
        check = check_ports(output(format=GEOJSON, ontology_url=EDAM), input_(format="rds"), service)
        assert check.reason == UnverifiedReason.UNKNOWN_ONTOLOGY

    def test_identical_formats_are_compatible_without_asking(self) -> None:
        def never_called(_pair: FormatPair) -> bool | None:
            raise AssertionError("lookup should not be consulted")

        check = check_ports(
            output(format=GEOJSON, ontology_url=EDAM), input_(format=GEOJSON, ontology_url=EDAM), never_called
        )
        assert check.status == COMPATIBLE

    def test_service_decides_different_formats(self, service) -> None:
        out = output(format=GEOPACKAGE, ontology_url=EDAM)
        assert check_ports(out, input_(format=VECTOR, ontology_url=EDAM), service).status == COMPATIBLE
        rejected = check_ports(out, input_(format=SHAPEFILE, format_label="Shapefile", ontology_url=EDAM), service)
        assert rejected.status == INCOMPATIBLE
        assert rejected.message == f"Incompatible formats - {GEOPACKAGE} cannot feed Shapefile"

    def test_unanswered_question_is_unverified(self) -> None:
        check = check_ports(output(format=GEOPACKAGE, ontology_url=EDAM), input_(format=VECTOR, ontology_url=EDAM))
        assert (check.status, check.reason) == (UNVERIFIED, UnverifiedReason.NOT_CHECKED)


def test_format_pairs_between_keeps_only_distinct_service_questions() -> None:
    outputs = [output(format=GEOJSON, ontology_url=EDAM), output(format=GEOJSON, ontology_url=EDAM), output()]
    inputs = [
        input_(format=VECTOR, ontology_url=EDAM),
        input_(format=GEOJSON, ontology_url=EDAM),  # identical format - decided locally
        input_(),  # no format - unverifiable
        input_(format=VECTOR, ontology_url=OTHER),  # another ontology
    ]
    assert format_pairs_between(outputs, inputs) == {
        FormatPair(actual_format=GEOJSON, expected_format=VECTOR, ontology_url=EDAM)
    }
