import json

import pytest

from app.infrastructure.cwl.canvas_graph import (
    CanvasFormatError,
    canvas_component_ids,
    node_component_id,
    parse_canvas,
    topological_sort,
)


def canvas(nodes: list, edges: list | None = None) -> str:
    return json.dumps({"nodes": nodes, "edges": edges or []})


def node(node_id: str, component_id: str | None) -> dict:
    return {"id": node_id, "data": {"componentId": component_id}}


def test_component_ids_are_distinct_and_in_node_order() -> None:
    state = canvas([node("a", "c2"), node("b", "c1"), node("c", "c2")])
    assert canvas_component_ids(state) == ["c2", "c1"]


def test_component_ids_skip_nodes_without_a_component() -> None:
    state = canvas([node("a", None), {"id": "b", "data": None}, {"id": "c"}, node("d", "c1")])
    assert canvas_component_ids(state) == ["c1"]


@pytest.mark.parametrize("state", ["not json", "[1, 2]", '{"nodes": {"a": 1}}', '{"nodes": [{"data": {}}]}'])
def test_component_ids_of_an_unreadable_canvas_are_empty(state: str) -> None:
    assert canvas_component_ids(state) == []


@pytest.mark.parametrize(
    "state",
    [
        "not json",
        "[1, 2]",
        '{"nodes": "x"}',
        '{"nodes": [{"data": {}}]}',
        '{"nodes": [{"id": 3}]}',
        '{"nodes": [{"id": "a"}], "edges": [1]}',
    ],
)
def test_parse_rejects_malformed_canvases_with_a_format_error(state: str) -> None:
    with pytest.raises(CanvasFormatError):
        parse_canvas(state)


def test_parse_tolerates_missing_or_null_collections() -> None:
    assert parse_canvas('{"nodes": null}') == ([], [])


def test_node_component_id_ignores_non_string_ids() -> None:
    assert node_component_id({"id": "a", "data": {"componentId": 42}}) is None
    assert node_component_id({"id": "a", "data": {"componentId": ""}}) is None


def test_topological_sort_ignores_edges_to_unknown_nodes() -> None:
    nodes, edges = parse_canvas(
        canvas([node("b", "x"), node("a", "x")], [{"source": "a", "target": "b"}, {"source": "a", "target": "gone"}])
    )
    assert [n["id"] for n in topological_sort(nodes, edges)] == ["a", "b"]
