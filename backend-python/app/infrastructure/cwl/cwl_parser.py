from typing import Any

import yaml  # dump only - reads go through load_cwl (PyYAML rejects valid CWL v1.2 flow scalars)

from app.domain.models.parameter import Parameter, ParameterDirection
from app.infrastructure.cwl.yaml_io import YAMLError, load_cwl


def inject_description(cwl_content: str, description: str | None) -> str:
    doc: Any = load_cwl(cwl_content)
    if description:
        doc["doc"] = description
    else:
        doc.pop("doc", None)
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, width=float("inf"), allow_unicode=True)


def inject_cwl_version(cwl_content: str, cwl_version: str | None) -> str:
    """Set/overwrite the top-level cwlVersion: on a standalone CWL document - used when
    persisting an inline-extracted CommandLineTool, which inherited its cwlVersion from
    the parent Workflow and has none of its own. No-op if cwl_version is None."""
    if cwl_version is None:
        return cwl_content
    doc: Any = load_cwl(cwl_content)
    doc["cwlVersion"] = cwl_version
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, width=float("inf"), allow_unicode=True)


def extract_description(cwl_content: str) -> str | None:
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
        return None
    return doc.get("doc") if isinstance(doc, dict) else None


#: CWL pulls other files in two ways: $import parses the target and splices the result in,
#: $include inserts it as raw text. For bundling purposes they are the same thing - a file
#: the document cannot do without.
_IMPORT_KEYS = ("$import", "$include")
#: not ours to bundle - the document keeps the URL and resolves it at run time
_REMOTE_PREFIXES = ("http://", "https://", "file://")


def collect_import_targets(cwl_content: str) -> set[str]:
    """Every local file referenced by $import/$include anywhere in the document.

    Paths come back exactly as written, because that is what has to resolve when the
    document is written back out - rewriting `types/spatial.yml` to `spatial.yml` would
    leave the $import pointing at nothing. A `#fragment` is stripped
    (`types.yml#ClusterSpec` -> `types.yml`): it selects a symbol inside the file, not a
    different file.

    Never raises - an unparseable document has no discoverable imports, and the callers
    that care about validity report that separately.
    """
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
        return set()

    targets: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _IMPORT_KEYS and isinstance(value, str):
                    target = value.split("#", 1)[0].strip()
                    if target and not target.lower().startswith(_REMOTE_PREFIXES):
                        targets.add(target)
                else:
                    walk(value)
        elif isinstance(node, list):
            for entry in node:
                walk(entry)

    walk(doc)
    return targets


def normalize_idmap(value: Any, key_field: str) -> dict[str, Any]:
    """CWL's idmap shorthand: `requirements`, `hints`, `inputs` and `outputs` may each be
    written either as a mapping keyed by class/id, or as a list of entries carrying that
    key inline. Both are valid CWL v1.2 - workflow_parser.normalize_steps does the same
    for `steps:`. Returns the mapping form.

        requirements: {DockerRequirement: {dockerPull: x}}
        requirements: [{class: DockerRequirement, dockerPull: x}]   -> identical result
    """
    if isinstance(value, dict):
        return value
    if not isinstance(value, list):
        return {}

    result: dict[str, Any] = {}
    for entry in value:
        if isinstance(entry, dict) and key_field in entry:
            # the key moves out of the body, matching how the mapping form is written
            result[entry[key_field]] = {k: v for k, v in entry.items() if k != key_field}
        elif isinstance(entry, str):
            # a bare name, e.g. `outputs: [result]` - present but undescribed
            result[entry] = {}
    return result


def _find_requirement(doc: dict, requirement_class: str) -> dict:
    """A requirement by class, looked up in `requirements` then `hints`.

    Both may carry a DockerRequirement, and hints is where tools that treat the container
    as advisory usually put it - reading only `requirements` would silently report such a
    tool as having no container at all.
    """
    for field in ("requirements", "hints"):
        found = normalize_idmap(doc.get(field), "class").get(requirement_class)
        if isinstance(found, dict):
            return found
    return {}


def extract_parameters(cwl_content: str) -> list[Parameter]:
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError as err:
        raise ValueError(f"YAML parse error: {err}") from err

    namespaces: dict[str, str] = (doc or {}).get("$namespaces") or {}
    # inputs/outputs accept the same idmap-or-list shorthand as requirements
    inputs = _extract_parameter_group(
        normalize_idmap((doc or {}).get("inputs"), "id"), ParameterDirection.INPUT, namespaces
    )
    outputs = _extract_parameter_group(
        normalize_idmap((doc or {}).get("outputs"), "id"), ParameterDirection.OUTPUT, namespaces
    )
    return inputs + outputs


def _extract_parameter_group(
    group: dict[str, Any], direction: ParameterDirection, namespaces: dict[str, str]
) -> list[Parameter]:
    parameters = []
    for name, definition in group.items():
        # Is the definition a dict, or flat string? e.g. input_rds: type: File is valid and no dict!
        is_mapping = isinstance(definition, dict)
        cwl_type = _stringify_type(definition.get("type", "string") if is_mapping else "string").rstrip("?")
        default_value = None
        description = None
        format_ = None
        if is_mapping:
            if definition.get("default") is not None:
                default_value = str(definition["default"])
            description = definition.get("doc")
            format_ = _resolve_format(definition.get("format"), namespaces)

        parameters.append(
            Parameter(
                name=name,
                cwl_type=cwl_type,
                default_value=default_value,
                description=description,
                format=format_,
                direction=direction,
            )
        )
    return parameters


def extract_cwl_type(cwl_content: str) -> str | None:
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
        return None
    return doc.get("class") if isinstance(doc, dict) else None


def extract_schema_url(cwl_content: str) -> str | None:
    """The ontology the document's `format` identifiers belong to - the first `$schemas`
    entry, e.g. http://edamontology.org/EDAM_1.18.owl. `$schemas` is a list per the CWL
    spec; a bare string is accepted too."""
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
        return None
    if not isinstance(doc, dict):
        return None
    schemas = doc.get("$schemas")
    if isinstance(schemas, str):
        return schemas
    if isinstance(schemas, list):
        return next((s for s in schemas if isinstance(s, str)), None)
    return None


def extract_dockerfile_content(cwl_content: str) -> str | None:
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
        return None
    if not isinstance(doc, dict):
        return None
    return _find_requirement(doc, "DockerRequirement").get("dockerFile")


def extract_docker_pull(cwl_content: str) -> str | None:
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
        return None
    if not isinstance(doc, dict):
        return None
    return _find_requirement(doc, "DockerRequirement").get("dockerPull")


def _resolve_format(format_value: Any, namespaces: dict[str, str]) -> str | None:
    # format is a (possibly namespaced) ontology identifier, e.g. "edam:format_2572"
    # with $namespaces: {edam: "http://edamontology.org/"} - expand to the full,
    # unambiguous identifier by prefixing with the namespace URL. Unprefixed values
    # (no matching $namespaces entry) are stored as-is.
    if not isinstance(format_value, str):
        return None
    prefix, sep, suffix = format_value.partition(":")
    if sep and prefix in namespaces:
        return f"{namespaces[prefix]}{suffix}"
    return format_value


def _stringify_type(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    if isinstance(value, dict) and value.get("type") == "array":
        return f"{_stringify_type(value.get('items', 'string'))}[]"
    return str(value)


def generate_inputs_yaml(parameters: list[Parameter], name: str, version: int) -> str:
    lines = [
        f"# CWL inputs for {name} v{version}",
        f"# Usage: cwltool {name}-v{version}.cwl inputs.yaml",
    ]
    for p in parameters:
        if not p.name:
            continue
        cwl_type = (p.cwl_type or "string").lower()
        lines.extend(_format_input(p.name, cwl_type, p.default_value))
    return "\n".join(lines) + "\n"


def _format_input(name: str, cwl_type: str, default_value: str | None) -> list[str]:
    if cwl_type == "file":
        return [f"{name}:", "  class: File", "  path: /path/to/input"]
    if cwl_type == "directory":
        return [f"{name}:", "  class: Directory", "  location: /path/to/dir"]
    if cwl_type in ("double", "float"):
        num = float(default_value) if default_value is not None else 0.0
        return [f"{name}: {num:.1f}" if num.is_integer() else f"{name}: {num}"]
    if cwl_type in ("int", "long"):
        num = int(default_value) if default_value is not None else 0
        return [f"{name}: {num}"]
    if cwl_type == "boolean":
        value = default_value == "true" if default_value is not None else False
        return [f"{name}: {str(value).lower()}"]
    return [f"{name}: {yaml.dump(default_value or '', allow_unicode=True).strip()}"]