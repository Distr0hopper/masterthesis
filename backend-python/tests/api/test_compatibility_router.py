"""The workflow builder's type checks over HTTP, with the ports loaded from the database:
POST /compatibility for the edges of a canvas, and GET /components?rankAgainst= for the
palette. The SOS File Format Service is faked - and counted, since its answers are cached
and its questions shared."""

import uuid
from collections.abc import Iterator

import httpx
import pytest

from app.application.service import compatibility_service
from app.domain.models.component import ComponentStatus
from app.domain.models.parameter import ParameterDirection
from app.infrastructure.format_service.format_service_client import FormatServiceClient
from tests.conftest import SessionFactory
from tests.db_factories import EO_FORMAT, bearer, port, save, tool, user

pytestmark = pytest.mark.anyio

IN, OUT = ParameterDirection.INPUT, ParameterDirection.OUTPUT


class FakeFormatService:
    """GeoJSON and GeoPackage are vectors, nothing is a raster - anything else is unknown,
    as if the service could not answer."""

    def __init__(self) -> None:
        self.questions: list[tuple[str, str]] = []
        self.down = False

    async def check_compatibility(self, expected_format: str, actual_format: str, ontology_url: str) -> bool | None:
        self.questions.append((actual_format.removeprefix(EO_FORMAT), expected_format.removeprefix(EO_FORMAT)))
        if self.down:
            return None
        expected = expected_format.removeprefix(EO_FORMAT)
        if expected == "Vector":
            return actual_format.removeprefix(EO_FORMAT) in ("GeoJSON", "GeoPackage")
        if expected == "Raster":
            return False
        return None


@pytest.fixture
def formats(client: httpx.AsyncClient) -> Iterator[FakeFormatService]:
    from app.main import app

    fake = FakeFormatService()
    app.dependency_overrides[FormatServiceClient.get_client] = lambda: fake
    # the answers are cached process-wide - a test must not see another's
    compatibility_service._cache.clear()
    yield fake
    compatibility_service._cache.clear()


def edge(source: object, source_port: str, target: object, target_port: str) -> dict:
    return {
        "sourceComponentId": str(source.id),  # type: ignore[attr-defined]
        "sourcePort": source_port,
        "targetComponentId": str(target.id),  # type: ignore[attr-defined]
        "targetPort": target_port,
    }


async def check(client: httpx.AsyncClient, *edges: dict, headers: dict | None = None) -> list[tuple[str, str | None]]:
    response = await client.post("/compatibility", json={"connections": list(edges)}, headers=headers)
    assert response.status_code == 200
    return [(r["status"], r["reason"]) for r in response.json()["results"]]


async def test_each_edge_gets_its_verdict_in_request_order(
    client: httpx.AsyncClient, sessions: SessionFactory, formats: FakeFormatService
) -> None:
    owner = user()
    geojson = tool("geojson-source", owner, ports=(port("out", OUT, "GeoJSON"),))
    untyped = tool("untyped-source", owner, ports=(port("out", OUT),))
    vectors = tool("vector-sink", owner, ports=(port("in", IN, "Vector"),))
    rasters = tool("raster-sink", owner, ports=(port("in", IN, "Raster"),))
    await save(sessions, owner, geojson, untyped, vectors, rasters)

    assert await check(
        client,
        edge(geojson, "out", vectors, "in"),
        edge(geojson, "out", rasters, "in"),
        edge(untyped, "out", vectors, "in"),
        edge(geojson, "nope", vectors, "in"),
    ) == [
        ("compatible", None),
        ("incompatible", None),
        ("unverified", "missing-output-format"),
        ("incompatible", None),
    ]
    # the untyped output and the unknown port never needed the service
    assert sorted(formats.questions) == [("GeoJSON", "Raster"), ("GeoJSON", "Vector")]


async def test_identical_formats_and_shared_questions_ask_the_service_once(
    client: httpx.AsyncClient, sessions: SessionFactory, formats: FakeFormatService
) -> None:
    owner = user()
    a = tool("a", owner, ports=(port("out", OUT, "GeoJSON"),))
    b = tool("b", owner, ports=(port("out", OUT, "GeoJSON"),))
    vectors = tool("vector-sink", owner, ports=(port("in", IN, "Vector"),))
    same = tool("geojson-sink", owner, ports=(port("in", IN, "GeoJSON"),))
    await save(sessions, owner, a, b, vectors, same)

    edges = (edge(a, "out", vectors, "in"), edge(b, "out", vectors, "in"), edge(a, "out", same, "in"))
    assert await check(client, *edges) == [("compatible", None)] * 3
    assert formats.questions == [("GeoJSON", "Vector")]

    # and a later request is answered from the cache
    await check(client, *edges)
    assert formats.questions == [("GeoJSON", "Vector")]


async def test_a_format_service_that_is_down_leaves_edges_unverified_and_uncached(
    client: httpx.AsyncClient, sessions: SessionFactory, formats: FakeFormatService
) -> None:
    owner = user()
    geojson = tool("geojson-source", owner, ports=(port("out", OUT, "GeoJSON"),))
    vectors = tool("vector-sink", owner, ports=(port("in", IN, "Vector"),))
    await save(sessions, owner, geojson, vectors)

    formats.down = True
    assert await check(client, edge(geojson, "out", vectors, "in")) == [("unverified", "not-checked")]
    formats.down = False
    # no answer was cached - the next request asks again and gets one
    assert await check(client, edge(geojson, "out", vectors, "in")) == [("compatible", None)]
    assert len(formats.questions) == 2


async def test_someone_elses_draft_is_an_unknown_component(
    client: httpx.AsyncClient, sessions: SessionFactory, formats: FakeFormatService
) -> None:
    owner, stranger = user(), user()
    source = tool("source", owner, ComponentStatus.DRAFT, ports=(port("out", OUT, "GeoJSON"),))
    sink = tool("sink", stranger, ports=(port("in", IN, "GeoJSON"),))
    await save(sessions, owner, stranger, source, sink)
    connection = edge(source, "out", sink, "in")

    assert await check(client, connection, headers=bearer(owner)) == [("compatible", None)]
    assert await check(client, connection, headers=bearer(stranger)) == [("incompatible", None)]
    assert await check(client, connection) == [("incompatible", None)]


async def test_too_many_connections_are_refused(client: httpx.AsyncClient, formats: FakeFormatService) -> None:
    some = {
        "sourceComponentId": str(uuid.uuid4()),
        "sourcePort": "o",
        "targetComponentId": str(uuid.uuid4()),
        "targetPort": "i",
    }
    response = await client.post("/compatibility", json={"connections": [some] * 10_000})
    assert response.status_code == 422


async def test_the_palette_ranks_what_fits_the_canvas_first(
    client: httpx.AsyncClient, sessions: SessionFactory, formats: FakeFormatService
) -> None:
    owner, stranger = user(), user()
    on_canvas = tool("on-canvas", owner, ports=(port("out", OUT, "GeoJSON"),))
    fits = tool("z-fits", owner, ports=(port("in", IN, "Vector"),))
    misfits = tool("a-misfits", owner, ports=(port("in", IN, "Raster"),))
    no_inputs = tool("b-no-inputs", owner)
    hidden = tool("c-hidden", stranger, ComponentStatus.DRAFT, ports=(port("in", IN, "Vector"),))
    await save(sessions, owner, stranger, on_canvas, fits, misfits, no_inputs, hidden)

    response = await client.get(
        "/components", params={"rankAgainst": [str(on_canvas.id)], "limit": 2}, headers=bearer(owner)
    )

    assert response.status_code == 200
    body = response.json()
    # every candidate is ranked before paging - the best fit is on page one despite its name
    assert [item["name"] for item in body["content"]] == ["z-fits", "a-misfits"]
    assert body["totalElements"] == 4
