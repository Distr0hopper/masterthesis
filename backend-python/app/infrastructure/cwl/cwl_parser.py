from typing import Any

import yaml

from app.domain.models.parameter import Parameter, ParameterDirection


def inject_description(cwl_content: str, description: str | None) -> str:
    doc: Any = yaml.safe_load(cwl_content)
    if description:
        doc["doc"] = description
    else:
        doc.pop("doc", None)
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, width=float("inf"))


def extract_description(cwl_content: str) -> str | None:
    try:
        doc: Any = yaml.safe_load(cwl_content)
    except yaml.YAMLError:
        return None
    return doc.get("doc") if isinstance(doc, dict) else None


def extract_parameters(cwl_content: str) -> list[Parameter]:
    try:
        doc: Any = yaml.safe_load(cwl_content)
    except yaml.YAMLError as err:
        raise ValueError(f"YAML parse error: {err}") from err

    namespaces: dict[str, str] = (doc or {}).get("$namespaces") or {}
    inputs = _extract_parameter_group((doc or {}).get("inputs") or {}, ParameterDirection.INPUT, namespaces)
    outputs = _extract_parameter_group((doc or {}).get("outputs") or {}, ParameterDirection.OUTPUT, namespaces)
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
        doc: Any = yaml.safe_load(cwl_content)
    except yaml.YAMLError:
        return None
    return doc.get("class") if isinstance(doc, dict) else None


def extract_dockerfile_content(cwl_content: str) -> str | None:
    try:
        doc: Any = yaml.safe_load(cwl_content)
    except yaml.YAMLError:
        return None
    if not isinstance(doc, dict):
        return None
    requirements = doc.get("requirements") or {}
    docker_requirement = requirements.get("DockerRequirement") or {}
    return docker_requirement.get("dockerFile")


def extract_docker_pull(cwl_content: str) -> str | None:
    try:
        doc: Any = yaml.safe_load(cwl_content)
    except yaml.YAMLError:
        return None
    if not isinstance(doc, dict):
        return None
    requirements = doc.get("requirements") or {}
    docker_requirement = requirements.get("DockerRequirement") or {}
    return docker_requirement.get("dockerPull")


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
    return [f"{name}: {yaml.dump(default_value or '').strip()}"]