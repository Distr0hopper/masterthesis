import pytest

from app.domain.compatibility.port import FormatLookup, FormatPair, Port
from app.domain.models.parameter import ParameterDirection

EDAM = "http://ontology/edam_eo.owl"
OTHER = "http://other.org/o.owl"
GEOJSON = "http://edamontology.org/format_4106"
GEOPACKAGE = "http://edamontology.org/format_4107"
VECTOR = "http://edamontology.org/format_4126"
SHAPEFILE = "http://edamontology.org/format_4119"


def input_(cwl_type: str = "File", name: str = "in", **kwargs) -> Port:
    return Port(name=name, cwl_type=cwl_type, direction=ParameterDirection.INPUT, **kwargs)


def output(cwl_type: str = "File", name: str = "out", **kwargs) -> Port:
    return Port(name=name, cwl_type=cwl_type, direction=ParameterDirection.OUTPUT, **kwargs)


def fake_service(pair: FormatPair) -> bool | None:
    """The format service, faked: GeoJSON and GeoPackage are vectors, nothing is a Shapefile."""
    if pair.expected_format == VECTOR and pair.actual_format in (GEOJSON, GEOPACKAGE):
        return True
    if pair.expected_format == SHAPEFILE:
        return False
    return None


@pytest.fixture
def service() -> FormatLookup:
    return fake_service
