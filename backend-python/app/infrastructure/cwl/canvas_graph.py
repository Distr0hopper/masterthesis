"""Graph operations over a workflow-builder canvas.

Nodes and edges arrive as the plain dicts the frontend serialised into
`WorkflowDraft.canvas_state`; nothing here touches the ORM or FastAPI.
"""

from collections import deque
from typing import Any


class CanvasCycleError(ValueError):
    """The canvas graph is not a DAG, so it has no valid step order."""


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
