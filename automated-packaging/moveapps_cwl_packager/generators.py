"""Generate Dockerfile, CWL CommandLineTool, and cwl-wrapper.sh."""

from __future__ import annotations

from typing import Any

import yaml

# ---------------------------------------------------------------------------
# Type mapping
# ---------------------------------------------------------------------------

_APPSPEC_TO_CWL: dict[str, str] = {
    "INTEGER": "int",
    "DOUBLE": "double",
    "FLOAT": "double",
    "STRING": "string",
    "BOOLEAN": "boolean",
    "CHECKBOX": "boolean",  
    "TIMESTAMP": "string",
    "DROPDOWN": "string",
    "RADIOBUTTON": "string",
    "INSTANT": "string",
}


def _cwl_type(appspec_type: str, optional: bool) -> str:
    base = _APPSPEC_TO_CWL.get(appspec_type.upper(), "string")
    return f"{base}?" if optional else base


# ---------------------------------------------------------------------------
# PyYAML helpers — force literal block scalars for JS expressions
# ---------------------------------------------------------------------------


class _LiteralStr(str):
    """String subclass that PyYAML renders as a literal block scalar (|)."""


def _literal_representer(
    dumper: yaml.Dumper, data: _LiteralStr
) -> yaml.ScalarNode:
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


def _make_dumper() -> type[yaml.Dumper]:
    class _Dumper(yaml.Dumper):
        pass

    _Dumper.add_representer(_LiteralStr, _literal_representer)
    # Keep None as empty (null)
    _Dumper.add_representer(
        type(None),
        lambda d, _: d.represent_scalar("tag:yaml.org,2002:null", ""),
    )
    return _Dumper


# ---------------------------------------------------------------------------
# Dockerfile-Content  (single per-app image extending the shared SDK base)
# Content goes into the generated .cwl file under DockerRequirement: dockerFile
# ---------------------------------------------------------------------------


def generate_dockerfile_content(wrapper_image: str, raw_base_url: str, r_packages: list[str] | None = None) -> str:
    lines = [f"FROM --platform=linux/amd64 {wrapper_image}", ""]
    if r_packages:
        pkg_vec = ", ".join(f'"{p}"' for p in r_packages)
        install_cmd = (
            f"RUN R -e 'pkgs <- c({pkg_vec}); "
            "missing <- pkgs[!sapply(pkgs, requireNamespace, quietly=TRUE)]; "
            "if (length(missing)) install.packages(missing, repos=\"https://cloud.r-project.org\")'"
        )
        lines += [install_cmd, ""]
    lines += [
        f"ADD --chown=moveapps:staff {raw_base_url}/RFunction.R /home/moveapps/co-pilot-r/RFunction.R",
        f"ADD --chown=moveapps:staff {raw_base_url}/app-configuration.json /home/moveapps/co-pilot-r/app-configuration.json",
        "RUN chmod o+r /home/moveapps/co-pilot-r/RFunction.R /home/moveapps/co-pilot-r/app-configuration.json",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CWL CommandLineTool
# ---------------------------------------------------------------------------


def _build_js_entry(settings: list[dict]) -> _LiteralStr:
    """Build the JavaScript expression for InitialWorkDirRequirement entry."""
    if not settings:
        pairs = "    // no parameters"
    else:
        pairs = ",\n".join(
            f"    {s['id']}: inputs.{s['id']}" for s in settings
        )
    js = f"${{\n  return JSON.stringify({{\n{pairs}\n  }});\n}}"
    return _LiteralStr(js)


def generate_cwl(
    app_name: str,
    settings: list[dict],
    dockerfile_content: str,
    description: str = "",
) -> str:
    """Return a CWL v1.2 CommandLineTool document as a YAML string."""

    # Build inputs dict — input_rds first, then app parameters
    inputs: dict[str, Any] = {
        "input_rds": {
            "type": "File",
            "doc": "Input RDS file (MoveStack or move2 object)",
            "inputBinding": {"position": 1},
        }
    }

    for setting in settings:
        sid = setting["id"]
        raw_type = setting.get("type", "STRING")
        default_val = setting.get("defaultValue")
        has_default = default_val is not None and default_val != ""

        entry: dict[str, Any] = {
            "type": _cwl_type(raw_type, optional=True),
            "doc": setting.get("description", ""),
        }
        if has_default:
            entry["default"] = _coerce_default(default_val, raw_type)

        inputs[sid] = entry

    doc: dict[str, Any] = {
        "cwlVersion": "v1.2",
        "class": "CommandLineTool",
        "doc": description or None,
        "requirements": {
            "InlineJavascriptRequirement": {},
            "DockerRequirement": {
                "dockerFile": dockerfile_content,
                "dockerImageId": app_name,
            },
            "InitialWorkDirRequirement": {
                "listing": [
                    {
                        "entryname": "app-configuration.json",
                        "entry": _build_js_entry(settings),
                    }
                ]
            },
        },
        "baseCommand": ["/home/moveapps/co-pilot-r/cwl-wrapper.sh"],
        "inputs": inputs,
        "outputs": {
            "output_rds": {
                "type": "File",
                "outputBinding": {"glob": "output.rds"},
            },
            "error_log": {
                "type": "File?",
                "outputBinding": {"glob": "error.log"},
            },
            "artifacts": {
                "type": {"type": "array", "items": "File"},
                "outputBinding": {"glob": "artifacts/*"},
            },
        },
    }

    Dumper = _make_dumper()
    return yaml.dump(
        doc,
        Dumper=Dumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )


def _coerce_default(value: Any, appspec_type: str) -> Any:
    """Return value in the appropriate Python type for the given appspec type."""
    t = appspec_type.upper()
    if t == "INTEGER":
        try:
            return int(value)
        except (TypeError, ValueError):
            return value
    if t in ("DOUBLE", "FLOAT"):
        try:
            return float(value)
        except (TypeError, ValueError):
            return value
    if t in ("BOOLEAN", "CHECKBOX"):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes")
        return bool(value)
    # STRING, TIMESTAMP, DROPDOWN, RADIOBUTTON → keep as string
    return str(value)


def generate_inputs_yaml(settings: list[dict], app_config: dict) -> str:
    """Return a CWL inputs YAML pre-filled with values from app-configuration.json."""
    inputs: dict[str, Any] = {
        "input_rds": {
            "class": "File",
            "path": "/path/to/your/input.rds",
        }
    }
    for setting in settings:
        sid = setting["id"]
        raw_type = setting.get("type", "STRING")
        value = app_config.get(sid, setting.get("defaultValue"))
        inputs[sid] = _coerce_default(value, raw_type) if value is not None else None

    Dumper = _make_dumper()
    return yaml.dump(
        inputs,
        Dumper=Dumper,
        default_flow_style=False,
        allow_unicode=True,
        sort_keys=False,
        width=120,
    )
