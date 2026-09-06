"""Turns a workflow-builder canvas into a CWL v1.2 Workflow document.

Framework-free: it takes plain canvas dicts plus a {component_id: PortSpec} map, so it is
directly unit-testable and has no dependency on the ORM or the request cycle.
"""

import re
from dataclasses import dataclass, field
from typing import Any

import yaml

CWL_VERSION = "v1.2"

# CWL scalars that must not be emitted as YAML strings, or cwltool rejects the type
_INT_TYPES = {"int", "long"}
_FLOAT_TYPES = {"float", "double"}
_BOOL_TYPES = {"boolean"}


@dataclass
class PortSpec:
    """The parts of a Component the generator needs, resolved from the DB."""

    name: str
    #: parameter name -> cwl type, for File-typed inputs
    file_inputs: dict[str, str] = field(default_factory=dict)
    #: parameter name -> cwl type, for File-typed outputs
    file_outputs: dict[str, str] = field(default_factory=dict)
    #: parameter name -> cwl type, for non-File inputs (the configurable knobs)
    config_inputs: dict[str, str] = field(default_factory=dict)


def _base_type(cwl_type: str) -> str:
    """`File?` and `File[]` both reduce to `file` for comparison purposes."""
    return cwl_type.replace("?", "").replace("[]", "").strip().lower()


def coerce_default(value: str, cwl_type: str) -> Any:
    """Parameter values are stored as strings by the builder; CWL needs real YAML scalars.

    An unparseable number falls back to the raw string rather than raising: a bad value
    should surface as a cwltool type error on the exported file, not as a failed export.
    """
    base = _base_type(cwl_type)
    if base in _BOOL_TYPES:
        return value.strip().lower() in {"true", "1", "yes"}
    if base in _INT_TYPES:
        try:
            return int(value)
        except ValueError:
            return value
    if base in _FLOAT_TYPES:
        try:
            return float(value)
        except ValueError:
            return value
    return value


def step_id_for(component_name: str) -> str:
    """`Remove Outliers` -> `step_remove_outliers`. CWL identifiers allow [A-Za-z0-9_-]."""
    slug = re.sub(r"[^a-z0-9]+", "_", component_name.lower()).strip("_")
    return f"step_{slug or 'component'}"


def cwl_filename_for(component_name: str) -> str:
    """`Remove Outliers` -> `remove-outliers.cwl`, the `run:` reference and zip entry."""
    slug = re.sub(r"[^a-z0-9]+", "-", component_name.lower()).strip("-")
    return f"{slug or 'component'}.cwl"


def safe_workflow_slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "workflow"


def _workflow_input_id(step_id: str, port_name: str) -> str:
    # namespaced by step, so two components that both take `input_rds` do not collide
    return f"{step_id}__{port_name}"


def generate_workflow_cwl(
    workflow_name: str,
    ordered_nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    ports: dict[str, PortSpec],
) -> str:
    """Build the main `class: Workflow` document.

    Wiring comes from each edge's `sourceHandle`/`targetHandle`, which carry the real
    parameter names - the canvas has one handle per port, so a connection already says
    exactly which output feeds which input.
    """
    # (target node, target port) -> (source node, source port)
    incoming: dict[tuple[str, str], tuple[str, str]] = {}
    # every (node, port) that something downstream consumes
    consumed: set[tuple[str, str]] = set()

    node_ids = {n["id"] for n in ordered_nodes}
    for edge in edges:
        source, target = edge.get("source"), edge.get("target")
        source_handle, target_handle = edge.get("sourceHandle"), edge.get("targetHandle")
        if source not in node_ids or target not in node_ids:
            continue
        if not source_handle or not target_handle:
            continue
        incoming[(target, target_handle)] = (source, source_handle)
        consumed.add((source, source_handle))

    step_ids: dict[str, str] = {}
    for node in ordered_nodes:
        component_name = ports[node["data"]["componentId"]].name
        step_id = step_id_for(component_name)
        # two nodes may reuse the same component; suffix so step ids stay unique
        if step_id in step_ids.values():
            suffix = sum(1 for existing in step_ids.values() if existing.startswith(step_id)) + 1
            step_id = f"{step_id}_{suffix}"
        step_ids[node["id"]] = step_id

    workflow_inputs: dict[str, Any] = {}
    steps: dict[str, Any] = {}

    for node in ordered_nodes:
        spec = ports[node["data"]["componentId"]]
        step_id = step_ids[node["id"]]
        step_in: dict[str, Any] = {}

        for port_name, cwl_type in spec.file_inputs.items():
            upstream = incoming.get((node["id"], port_name))
            if upstream:
                source_node_id, source_port = upstream
                step_in[port_name] = f"{step_ids[source_node_id]}/{source_port}"
            else:
                # nothing feeds this port, so it becomes an input of the whole workflow
                input_id = _workflow_input_id(step_id, port_name)
                workflow_inputs[input_id] = {"type": cwl_type}
                step_in[port_name] = input_id

        # configured knobs ride along as step-level defaults, keeping the workflow's own
        # input interface limited to actual data files
        parameter_values: dict[str, str] = node["data"].get("parameterValues") or {}
        for port_name, cwl_type in spec.config_inputs.items():
            raw = parameter_values.get(port_name)
            if raw is None or raw == "":
                continue
            step_in[port_name] = {"default": coerce_default(raw, cwl_type)}

        steps[step_id] = {
            "run": cwl_filename_for(spec.name),
            "in": step_in,
            "out": list(spec.file_outputs.keys()),
        }

    # anything no downstream step consumes is a result of the workflow
    workflow_outputs: dict[str, Any] = {}
    for node in ordered_nodes:
        spec = ports[node["data"]["componentId"]]
        step_id = step_ids[node["id"]]
        for port_name, cwl_type in spec.file_outputs.items():
            if (node["id"], port_name) in consumed:
                continue
            workflow_outputs[f"{step_id}__{port_name}"] = {
                "type": cwl_type,
                "outputSource": f"{step_id}/{port_name}",
            }

    doc = {
        "cwlVersion": CWL_VERSION,
        "class": "Workflow",
        "label": workflow_name,
        "inputs": workflow_inputs,
        "outputs": workflow_outputs,
        "steps": steps,
    }

    # sort_keys=False preserves the logical document order (cwlVersion -> class -> ...)
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)
