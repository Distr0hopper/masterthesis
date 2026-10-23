"""Which `$schemas` entry a component's formats belong to, and how it is stored - two
components are only comparable when they name the same ontology."""

import pytest

from app.application.service.components_service import ComponentsService
from app.infrastructure.format_service.ontology import EO_FORMATS_SCHEMA_URL, resolve_ontology_url

EDAM = "http://edamontology.org/EDAM_1.18.owl"
SOS_CWL = "https://dfg-sos.github.io/ontologies/cwl.owl"


@pytest.mark.parametrize(
    "alias",
    [
        EO_FORMATS_SCHEMA_URL,
        "https://dfg-sos.github.io/ontologies/eo-formats",
        "https://dfg-sos.github.io/ontologies/eo-formats#",
        "https://dfg-sos.github.io/ontologies/eo-formats/",
        "https://dfg-sos.github.io/ontologies/releases/eo-formats/1.0.0/eo-formats.owl",
        "https://dfg-sos.github.io/ontologies/releases/eo-formats/1.1.0/eo-formats.owl",
    ],
)
def test_every_name_of_the_eo_formats_ontology_is_stored_as_its_schema_url(alias: str) -> None:
    assert resolve_ontology_url([alias]) == EO_FORMATS_SCHEMA_URL


def test_any_other_ontology_is_stored_as_declared() -> None:
    assert resolve_ontology_url([EDAM]) == EDAM
    # same site, different ontology - not an alias
    assert resolve_ontology_url([SOS_CWL]) == SOS_CWL
    assert resolve_ontology_url([]) is None


@pytest.mark.parametrize("schemas", [[SOS_CWL, EO_FORMATS_SCHEMA_URL], [EO_FORMATS_SCHEMA_URL, SOS_CWL]])
def test_the_eo_formats_ontology_wins_wherever_it_is_listed(schemas: list[str]) -> None:
    # cwl.owl only adds fields like sos:expectedCRS - the formats are never its
    assert resolve_ontology_url(schemas) == EO_FORMATS_SCHEMA_URL


def test_without_the_eo_formats_ontology_the_first_entry_is_taken() -> None:
    assert resolve_ontology_url([EDAM, "http://other.org/o.owl"]) == EDAM


def test_a_cwl_listing_the_cwl_extensions_first_still_gets_its_format_ontology() -> None:
    cwl = f"""
cwlVersion: v1.2
class: CommandLineTool
$namespaces:
  eo: https://dfg-sos.github.io/ontologies/eo-formats#
  sos: https://dfg-sos.github.io/ontologies/cwl#
$schemas:
  - {SOS_CWL}
  - {EO_FORMATS_SCHEMA_URL}
inputs: {{}}
outputs:
  roads:
    type: File
    format: eo:GeoJSON
    sos:expectedCRS: "EPSG:4326"
"""
    assert ComponentsService.ontology_url_for(cwl) == EO_FORMATS_SCHEMA_URL
