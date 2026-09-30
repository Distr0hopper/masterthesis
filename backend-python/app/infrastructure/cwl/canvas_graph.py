"""Graph operations over a workflow-builder canvas.

Nodes and edges arrive as the plain dicts the frontend serialised into
`WorkflowDraft.canvas_state`; nothing here touches the ORM or FastAPI.
"""

import json
from collections import deque
from typing import Any


class CanvasCycleError(ValueError):
    """The canvas graph is not a DAG, so it has no valid step order."""


class CanvasFormatError(ValueError):
    """canvas_state is not the {nodes, edges} shape the builder writes."""


def parse_canvas(canvas_state: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(nodes, edges) from a stored canvas, validated just far enough that graph code can
    index `node["id"]` and `node["data"]` without crashing. The canvas schema belongs to
    the frontend, so anything malformed is a user-facing format error, never a 500."""
    try:
        canvas = json.loads(canvas_state)
    except json.JSONDecodeError as err:
        raise CanvasFormatError("The saved canvas could not be read") from err
    if not isinstance(canvas, dict):
        raise CanvasFormatError("The saved canvas could not be read")

    nodes = canvas.get("nodes") or []
    edges = canvas.get("edges") or []
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise CanvasFormatError("The saved canvas could not be read")
    if not all(isinstance(n, dict) and isinstance(n.get("id"), str) for n in nodes):
        raise CanvasFormatError("The saved canvas contains a node without an id")
    if not all(isinstance(e, dict) for e in edges):
        raise CanvasFormatError("The saved canvas contains an unreadable connection")
    return nodes, edges


def node_component_id(node: dict[str, Any]) -> str | None:
    """The component a canvas node was dropped from, or None if it carries none."""
    data = node.get("data")
    component_id = data.get("componentId") if isinstance(data, dict) else None
    return component_id if isinstance(component_id, str) and component_id else None


def canvas_component_ids(canvas_state: str) -> list[str]:
    """Every distinct componentId on a canvas, in node order. Lenient: an unreadable
    canvas simply references nothing - callers that need a hard failure use parse_canvas."""
    try:
        nodes, _edges = parse_canvas(canvas_state)
    except CanvasFormatError:
        return []
    return list(dict.fromkeys(cid for n in nodes if (cid := node_component_id(n)) is not None))


def topological_sort(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Kahn's algorithm - returns nodes in execution order (source before target).

    Visual position on the canvas says nothing about execution order, so the edge graph
    is the only source of truth here.
    """
    id_to_node = {n["id"]: n for n in nodes}
    in_degree: dict[str, int] = {n["id"]: 0 for n in nodes}
    adjacency: dict[str, list[str]] = {n["id"]: [] for n in nodes}

    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        # an edge pointing at a node that is no longer on the canvas would corrupt the
        # in-degree bookkeeping and silently drop nodes from the result
        if source not in id_to_node or target not in id_to_node:
            continue
        adjacency[source].append(target)
        in_degree[target] += 1

    # sorted() keeps the output deterministic: several roots are otherwise ordered by
    # dict iteration, which would make the generated CWL churn between exports
    queue = deque(sorted(nid for nid, degree in in_degree.items() if degree == 0))
    ordered: list[dict[str, Any]] = []

    while queue:
        nid = queue.popleft()
        ordered.append(id_to_node[nid])
        for neighbour in sorted(adjacency[nid]):
            in_degree[neighbour] -= 1
            if in_degree[neighbour] == 0:
                queue.append(neighbour)

    if len(ordered) != len(nodes):
        raise CanvasCycleError("Workflow contains a cycle - CWL requires a directed acyclic graph")

    return ordered
