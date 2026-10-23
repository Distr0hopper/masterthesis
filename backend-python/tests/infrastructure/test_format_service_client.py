"""What goes over the wire to the SOS File Format Service, and what is read back."""

import asyncio
import json

import httpx

from app.infrastructure.format_service.format_service_client import FormatServiceClient

EO = "https://dfg-sos.github.io/ontologies/eo-formats.owl"
GEOTIFF = "https://dfg-sos.github.io/ontologies/eo-formats#GeoTIFF"
COG = "https://dfg-sos.github.io/ontologies/eo-formats#COG"


def _client(handler) -> FormatServiceClient:
    return FormatServiceClient("http://format/api/v1/", timeout=5, transport=httpx.MockTransport(handler))


def test_a_label_is_looked_up_by_format_and_ontology():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://format/api/v1/format-info"
        assert json.loads(request.content) == {"format_identifier": GEOTIFF, "ontology_schema_url": EO}
        return httpx.Response(200, json={"label": "GeoTIFF", "comment": "ignored"})

    assert asyncio.run(_client(handler).get_format_label(GEOTIFF, EO)) == "GeoTIFF"


def test_compatibility_asks_whether_the_output_satisfies_the_input():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "http://format/api/v1/compatibility"
        assert json.loads(request.content) == {
            "expected_format": GEOTIFF,
            "actual_format": COG,
            "ontology_schema_url": EO,
        }
        return httpx.Response(200, json={"compatible": True, "message": "ignored"})

    assert asyncio.run(_client(handler).check_compatibility(GEOTIFF, COG, EO)) is True


def test_a_failing_service_is_no_answer_not_an_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"detail": {"unknown_formats": [GEOTIFF]}})

    client = _client(handler)
    assert asyncio.run(client.get_format_label(GEOTIFF, EO)) is None
    assert asyncio.run(client.check_compatibility(GEOTIFF, COG, EO)) is None
