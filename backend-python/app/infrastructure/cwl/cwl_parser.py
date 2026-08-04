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

    inputs: dict[str, Any] = (doc or {}).get("inputs") or {}

    parameters = []
    for name, definition in inputs.items():
        # Is input description a dict, or flat string?
        # e.g. input_rds: type: File is valid and no dict!
        is_mapping = isinstance(definition, dict)
        cwl_type = _stringify_type(definition.get("type", "string") if is_mapping else "string").rstrip("?")
        default_value = None
        description = None
        if is_mapping:
            if definition.get("default") is not None:
                default_value = str(definition["default"])
            description = definition.get("doc")

        parameters.append(
            Parameter(
                name=name,
                cwl_type=cwl_type,
                default_value=default_value,
                description=description,
                direction=ParameterDirection.INPUT,
            )
        )
    return parameters


def _stringify_type(value: Any) -> str:
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
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