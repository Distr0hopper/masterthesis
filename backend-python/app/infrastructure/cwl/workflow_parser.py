from dataclasses import dataclass
from typing import Any

import yaml


@dataclass
class ParsedWorkflowStep:
    step_id: str  # the key under `steps:`, e.g. "step_remove_outliers"
    run_reference: str  # the `run:` value, e.g. "remove-outliers.cwl"
    order: int


def is_workflow_cwl(cwl_content: str) -> bool:
    try:
        doc: Any = yaml.safe_load(cwl_content)
    except yaml.YAMLError:
        return False
    return isinstance(doc, dict) and doc.get("class") == "Workflow"


def find_workflow_file(files: dict[str, str]) -> tuple[str, str]:
    """Given {filename: content} extracted from the uploaded zip, returns the (filename,
    content) of the one file whose `class` is `Workflow`. The main pipeline is identified
    by content, not filename, since the user may name it anything. Raises ValueError if
    zero or more than one such file is found."""
    matches = [(name, content) for name, content in files.items() if is_workflow_cwl(content)]
    if len(matches) == 0:
        raise ValueError("No CWL file with class: Workflow found in the archive")
    if len(matches) > 1:
        names = ", ".join(name for name, _ in matches)
        raise ValueError(f"Multiple CWL files with class: Workflow found ({names}); expected exactly one")
    return matches[0]


def extract_workflow_steps(cwl_content: str) -> list[ParsedWorkflowStep]:
    """Parses a `class: Workflow` CWL document and returns its steps in declaration order.

    Raises ValueError if `class` is not `Workflow`, `steps:` is missing/malformed, or a
    step's `run:` isn't a plain filename string (inline embedded tools under `run:` are
    out of scope - the workflow upload must reference separate .cwl files by name)."""
    try:
        doc: Any = yaml.safe_load(cwl_content)
    except yaml.YAMLError as err:
        raise ValueError(f"YAML parse error: {err}") from err

    if not isinstance(doc, dict):
        raise ValueError("CWL document must be a mapping")
    if doc.get("class") != "Workflow":
        raise ValueError(f"class is '{doc.get('class')}', expected 'Workflow'")

    steps = doc.get("steps")
    if not isinstance(steps, dict) or not steps:
        raise ValueError("Workflow has no steps")

    parsed: list[ParsedWorkflowStep] = []
    for order, (step_id, definition) in enumerate(steps.items()):
        if not isinstance(definition, dict) or "run" not in definition:
            raise ValueError(f"Step '{step_id}' is missing a 'run:' reference")
        run_value = definition["run"]
        if not isinstance(run_value, str):
            raise ValueError(f"Step '{step_id}' has a non-filename 'run:' value (inline tools are not supported)")
        parsed.append(ParsedWorkflowStep(step_id=step_id, run_reference=run_value, order=order))
    return parsed
