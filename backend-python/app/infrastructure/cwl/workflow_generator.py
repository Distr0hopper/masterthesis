"""Turns a workflow-builder canvas into a CWL v1.2 Workflow document.

Framework-free: it takes plain canvas dicts plus a {component_id: PortSpec} map, so it is
directly unit-testable and has no dependency on the ORM or the request cycle.
"""

import io
import posixpath
import re
import zipfile
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
    """The parts of a Component the generator needs, resolved from the DB - a tool or,
    nested, a workflow: both expose their ports the same way."""

    name: str
    #: parameter name -> cwl type, for File-typed inputs
    file_inputs: dict[str, str] = field(default_factory=dict)
    #: parameter name -> cwl type, for File-typed outputs
    file_outputs: dict[str, str] = field(default_factory=dict)
    #: parameter name -> cwl type, for non-File inputs (the configurable knobs)
    config_inputs: dict[str, str] = field(default_factory=dict)
    #: parameter name -> the knob's type exactly as the component's document declares it
    #: (`int?`, an inline enum, ...). Only knobs listed here can be redeclared as workflow
    #: inputs - the stored `config_inputs` type is lossy (no `?`, enums stringified)
    config_types: dict[str, Any] = field(default_factory=dict)
    #: parameter name -> the component's own default for that knob, if it declares one
    config_defaults: dict[str, Any] = field(default_factory=dict)


#: CWL types a workflow can redeclare without the component's SchemaDefRequirement / $import
_PORTABLE_TYPES = {"null", "boolean", "int", "long", "float", "double", "string", "file", "directory", "any"}


def portable_type(cwl_type: Any) -> Any | None:
    """The type to declare a workflow input with, or None if it can't stand on its own
    there - a record, or a named type that only resolves inside the component's document.

    Inline enums lose their `name`: two steps redeclaring the same enum must not collide.
    """
    if isinstance(cwl_type, str):
        base = cwl_type.removesuffix("?")
        while base.endswith("[]"):
            base = base.removesuffix("[]")
        return cwl_type if base.lower() in _PORTABLE_TYPES else None
    if isinstance(cwl_type, list):
        members = [portable_type(member) for member in cwl_type]
        return members if members and all(m is not None for m in members) else None
    if isinstance(cwl_type, dict):
        if cwl_type.get("type") == "array":
            items = portable_type(cwl_type.get("items"))
            return {"type": "array", "items": items} if items is not None else None
        symbols = cwl_type.get("symbols")
        if cwl_type.get("type") == "enum" and isinstance(symbols, list) and all(isinstance(s, str) for s in symbols):
            return {"type": "enum", "symbols": symbols}
    return None


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


def assemble_cwl_zip(
    workflow_name: str,
    pipeline_cwl: str,
    step_files: list[tuple[str, str]],
    extra_files: list[tuple[str, str]] | None = None,
) -> tuple[str, bytes]:
    """Zip a pipeline CWL together with its step CWLs, one consistent layout.

    Shared by the builder's "Export CWL" and the published-workflow "Download" so both
    archives are named and laid out identically:
      - archive:   ``{slug}.zip``
      - main doc:  ``{slug}.cwl`` (``{slug}-workflow.cwl`` if a step file already claims
                   that name)
      - step docs: written at the paths the caller passes - both lay a tree out the same
                   way (composite.tree.ArchiveLayout): a step's document next to the
                   pipeline running it, each nested workflow in a folder of its own
                   (``inner/inner.cwl``, its steps beside it).
      - extras:    ``$import``/``$include`` targets, written at their *paths* next to the
                   document importing them (e.g. ``types/spatial.yml``) rather than
                   flattened, so the import in the CWL still resolves.

    Returns ``(archive_filename, zip_bytes)``.
    """
    slug = safe_workflow_slug(workflow_name)

    step_names = {name for name, _ in step_files}
    main_filename = f"{slug}.cwl"
    if main_filename in step_names:
        main_filename = f"{slug}-workflow.cwl"

    # every path is relative to the main document - one that climbs out of its folder (an
    # upload's `$import: ../types/x.yml`) needs the documents one folder down for it to
    # resolve, or the entry would point outside the archive
    base = _documents_folder([name for name, _ in step_files] + [path for path, _ in extra_files or []])

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(_archive_path(base, main_filename), pipeline_cwl)
        for name, content in step_files:
            archive.writestr(_archive_path(base, name), content)
        for path, content in extra_files or []:
            archive.writestr(_archive_path(base, path), content)

    return f"{slug}.zip", buffer.getvalue()


def _documents_folder(paths: list[str]) -> str:
    """Where the CWL documents go so no path relative to them leaves the archive - "" when
    none climbs up, else as many folders as the deepest `../` needs."""
    depth = 0
    for path in paths:
        climbed = 0
        for part in posixpath.normpath(path).split("/"):
            if part != "..":
                break
            climbed += 1
        depth = max(depth, climbed)
    return "/".join(["workflow"] * depth)


def _archive_path(base: str, path: str) -> str:
    """`path` relative to the documents' folder, as an entry inside the archive."""
    return posixpath.normpath(posixpath.join(base, path)).lstrip("/")


def _workflow_input_id(step_id: str, port_name: str) -> str:
    # namespaced by step, so two components that both take `input_rds` do not collide
    return f"{step_id}__{port_name}"


def render_workflow_cwl(workflow_doc: dict[str, Any]) -> str:
    """A document from build_workflow_document as the .cwl file's YAML."""
    # sort_keys=False preserves the logical document order (cwlVersion -> class -> ...)
    return yaml.dump(workflow_doc, default_flow_style=False, sort_keys=False, allow_unicode=True)


def assign_step_ids(ordered_nodes: list[dict[str, Any]], ports: dict[str, PortSpec]) -> dict[str, str]:
    """{node id: CWL step id} - named after each node's component, suffixed where two
    nodes reuse the same component, so step ids stay unique."""
    step_ids: dict[str, str] = {}
    for node in ordered_nodes:
        component_name = ports[node["data"]["componentId"]].name
        step_id = step_id_for(component_name)
        if step_id in step_ids.values():
            suffix = sum(1 for existing in step_ids.values() if existing.startswith(step_id)) + 1
            step_id = f"{step_id}_{suffix}"
        step_ids[node["id"]] = step_id
    return step_ids


def build_workflow_document(
    workflow_name: str,
    ordered_nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    ports: dict[str, PortSpec],
    has_subworkflows: bool = False,
) -> dict[str, Any]:
    """Build the main `class: Workflow` document.

    Wiring comes from each edge's `sourceHandle`/`targetHandle`, which carry the real
    parameter names - the canvas has one handle per port, so a connection already says
    exactly which output feeds which input. `has_subworkflows` declares the requirement
    CWL needs before a step may run another workflow.
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

    step_ids = assign_step_ids(ordered_nodes, ports)

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

        # every knob becomes a workflow input too, so it can be changed in the job file
        # without touching the component. The value configured on the canvas - else the
        # component's own default - is the input's default, so the workflow still runs as
        # configured when the job file leaves it out.
        parameter_values: dict[str, str] = node["data"].get("parameterValues") or {}
        for port_name, cwl_type in spec.config_inputs.items():
            raw = parameter_values.get(port_name)
            configured = None if raw is None or raw == "" else coerce_default(raw, cwl_type)
            declared_type = portable_type(spec.config_types.get(port_name))
            if declared_type is None:
                # a type only the component's document can resolve: bake the value in instead
                if configured is not None:
                    step_in[port_name] = {"default": configured}
                continue
            input_id = _workflow_input_id(step_id, port_name)
            definition: dict[str, Any] = {"type": declared_type}
            default = configured if configured is not None else spec.config_defaults.get(port_name)
            if default is not None:
                definition["default"] = default
            workflow_inputs[input_id] = definition
            step_in[port_name] = input_id

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

    document: dict[str, Any] = {
        "cwlVersion": CWL_VERSION,
        "class": "Workflow",
        "label": workflow_name,
    }
    if has_subworkflows:
        document["requirements"] = [{"class": "SubworkflowFeatureRequirement"}]
    return {**document, "inputs": workflow_inputs, "outputs": workflow_outputs, "steps": steps}


def generate_workflow_inputs_yaml(workflow_name: str, workflow_doc: dict[str, Any]) -> str:
    """A job file (inputs.yaml) for a generated workflow: one entry per workflow input,
    ready for `cwltool <workflow>.cwl <this file>`.

    Reads the inputs of the very document build_workflow_document produced, so the two
    files always agree. Those inputs are the File ports nothing on the canvas feeds - a
    placeholder path to fill in - and every step's configuration, pre-filled with the
    value it defaults to in the .cwl, to be changed right here.
    """
    slug = safe_workflow_slug(workflow_name)
    lines = [
        f"# CWL inputs for {workflow_name}",
        "# Replace each placeholder path with your data, adjust the step configuration, then run:",
        f"#   cwltool {slug}.cwl {slug}-inputs.yaml",
    ]
    inputs: dict[str, dict[str, Any]] = workflow_doc.get("inputs") or {}
    if not inputs:
        lines += ["# Every input of this workflow is wired on the canvas - it needs no input files.", "{}"]
        return "\n".join(lines) + "\n"

    data = {k: v for k, v in inputs.items() if _is_data_placeholder(v)}
    config = {k: v for k, v in inputs.items() if k not in data}

    if data:
        lines += ["", "# --- Input data ---"]
        for input_id, definition in data.items():
            step_id, _, port_name = input_id.partition("__")
            lines.append("")
            lines.append(f"# {port_name} of {step_id} ({describe_type(definition.get('type'))})")
            lines.extend(_placeholder_entry(input_id, port_name or input_id, definition.get("type")))

    if config:
        lines += ["", "# --- Step configuration ---"]
        current_step = None
        for input_id, definition in config.items():
            step_id, _, port_name = input_id.partition("__")
            if step_id != current_step:
                lines += ["", f"# {step_id}"]
                current_step = step_id
            note = describe_type(definition.get("type"))
            if "default" not in definition:
                note += ", required" if not _is_optional(definition.get("type")) else ""
            lines.append(f"# {port_name} ({note})")
            lines.append(_value_entry(input_id, definition.get("default")))
    return "\n".join(lines) + "\n"


def describe_type(cwl_type: Any) -> str:
    """A CWL type as a short human-readable comment: `int?`, `string[]`, `enum: a, b`."""
    if isinstance(cwl_type, list):
        members = [describe_type(m) for m in cwl_type if m != "null"]
        text = " | ".join(members)
        return f"{text}?" if "null" in cwl_type else text
    if isinstance(cwl_type, dict):
        if cwl_type.get("type") == "array":
            return f"{describe_type(cwl_type.get('items'))}[]"
        if cwl_type.get("type") == "enum":
            return "enum: " + ", ".join(str(s).rsplit("/", 1)[-1] for s in cwl_type.get("symbols") or [])
    return str(cwl_type if cwl_type is not None else "File")


def _is_optional(cwl_type: Any) -> bool:
    if isinstance(cwl_type, str):
        return cwl_type.endswith("?")
    return isinstance(cwl_type, list) and "null" in cwl_type


def _file_class(cwl_type: Any) -> str | None:
    """`File` / `Directory` for a (possibly optional or array) file-like type, else None."""
    if isinstance(cwl_type, list):
        members = [m for m in cwl_type if m != "null"]
        return _file_class(members[0]) if len(members) == 1 else None
    if isinstance(cwl_type, dict) and cwl_type.get("type") == "array":
        return _file_class(cwl_type.get("items"))
    if isinstance(cwl_type, str):
        base = _base_type(cwl_type)
        return {"file": "File", "directory": "Directory"}.get(base)
    return None


def _is_array(cwl_type: Any) -> bool:
    if isinstance(cwl_type, list):
        return any(_is_array(m) for m in cwl_type if m != "null")
    if isinstance(cwl_type, dict):
        return cwl_type.get("type") == "array"
    return isinstance(cwl_type, str) and cwl_type.removesuffix("?").endswith("[]")


def _is_data_placeholder(definition: dict[str, Any]) -> bool:
    # a File/Directory nobody gave a value - the user has to point it at their data
    return "default" not in definition and _file_class(definition.get("type")) is not None


def _placeholder_entry(input_id: str, port_name: str, cwl_type: Any) -> list[str]:
    """One File/Directory input in job-file form. Arrays get one example element; optional
    inputs are still written out, since leaving them in is harmless and easier to fill in."""
    cls = _file_class(cwl_type) or "File"
    location = "path" if cls == "File" else "location"
    placeholder = f"/path/to/{port_name}"
    if _is_array(cwl_type):
        return [f"{input_id}:", f"  - class: {cls}", f"    {location}: {placeholder}"]
    return [f"{input_id}:", f"  class: {cls}", f"  {location}: {placeholder}"]


def _value_entry(input_id: str, value: Any) -> str:
    # null for a knob without a value: fine for an optional one, a clear error for a required one
    return yaml.safe_dump({input_id: value}, default_flow_style=False, sort_keys=False, allow_unicode=True).rstrip()
