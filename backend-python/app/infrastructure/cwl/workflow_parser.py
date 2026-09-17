import re
from dataclasses import dataclass
from typing import Any

import yaml  # dump only - reads go through load_cwl (PyYAML rejects valid CWL v1.2 flow scalars)

from app.infrastructure.cwl.yaml_io import YAMLError, load_cwl


@dataclass
class ParsedWorkflowStep:
    step_id: str  # the key under `steps:`, e.g. "step_remove_outliers"
    run_reference: str  # the `run:` value, e.g. "remove-outliers.cwl"
    order: int


def is_workflow_cwl(cwl_content: str) -> bool:
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
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
        doc: Any = load_cwl(cwl_content)
    except YAMLError as err:
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


def normalize_steps(steps: Any) -> list[tuple[str, dict]]:
    """Accepts CWL `steps:` in either idmap form (`{step_id: {...}}`) or explicit list
    form (`[{id: step_id, ...}, ...]`) - both are valid CWL v1.2. Returns
    [(step_id, step_def), ...] in declaration order.
    """
    if isinstance(steps, dict) and steps:
        return list(steps.items())
    if isinstance(steps, list) and steps:
        result: list[tuple[str, dict]] = []
        for entry in steps:
            if not isinstance(entry, dict) or "id" not in entry:
                raise ValueError("List-form step is missing an 'id' field")
            result.append((entry["id"], entry))
        return result
    raise ValueError("Workflow has no steps")


def _step_id_to_name(step_id: str) -> str:
    """`step_remove_outliers` -> `remove-outliers`, a starting point for a Component name."""
    name = step_id.removeprefix("step_").removeprefix("step-")
    return re.sub(r"[_\s]+", "-", name).lower()


def strip_cwl_extension(filename: str) -> str:
    """`remove-outliers.cwl` -> `remove-outliers`."""
    return filename[:-4] if filename.lower().endswith(".cwl") else filename


@dataclass
class WorkflowOverview:
    """Cheap workflow-level facts read alongside inline-component extraction."""

    # from label or filename as fallback
    name: str | None
    step_count: int
    external_refs: list[str]  # `run:` values that are plain filenames
    #: step ids whose `run:` is an inline mapping but not `class: CommandLineTool` (e.g. an
    #: inline ExpressionTool or sub-Workflow) - not returned by extract_inline_components
    #: and not a filename either, so callers need this to know step_count still accounts
    #: for them.
    unsupported_inline_steps: list[str]
    #: the document's own top-level cwlVersion:, if any - inline-extracted tools have none
    #: of their own (they inherit it from the parent Workflow), so persisting one needs
    #: this to inject a valid cwlVersion via cwl_parser.inject_cwl_version.
    cwl_version: str | None


@dataclass
class ExtractedComponent:
    """An inline CommandLineTool extracted from a self-contained workflow."""

    step_id: str
    suggested_name: str
    # the inline tool re-serialised as its own YAML document. NOTE: it has no top-level
    # cwlVersion of its own (inline tools inherit it from the parent Workflow) - a later
    # persistence step needs to inject one before this is valid as a standalone CWL file.
    cwl_content: str
    description: str | None
    inputs: list[dict]
    outputs: list[dict]


def is_self_contained(cwl_content: str) -> bool:
    """True iff the document is a valid `class: Workflow` with at least one step whose
    `run:` is an inline `{class: CommandLineTool, ...}` mapping rather than a filename.
    Never raises - any parse or structural problem is just "not self-contained"."""
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
        return False
    if not isinstance(doc, dict) or doc.get("class") != "Workflow":
        return False
    try:
        steps = normalize_steps(doc.get("steps"))
    except ValueError:
        return False
    return any(
        isinstance(definition.get("run"), dict) and definition["run"].get("class") == "CommandLineTool"
        for _step_id, definition in steps
    )


def read_workflow_overview(cwl_content: str) -> WorkflowOverview:
    """Step count, external step references and the workflow's own name/doc.

    Same validation as extract_workflow_steps (raises ValueError with an equivalent
    message on the same problems), except this does NOT reject inline `run:` mappings -
    step_count always comes from an independent len(steps), never derived by summing
    external_refs/extracted-components counts, since a step whose inline `run:` isn't a
    CommandLineTool (see unsupported_inline_steps) would otherwise silently vanish from
    both.
    """
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError as err:
        raise ValueError(f"YAML parse error: {err}") from err

    if not isinstance(doc, dict):
        raise ValueError("CWL document must be a mapping")
    if doc.get("class") != "Workflow":
        raise ValueError(f"class is '{doc.get('class')}', expected 'Workflow'")

    steps = normalize_steps(doc.get("steps"))

    external_refs: list[str] = []
    unsupported_inline_steps: list[str] = []
    for step_id, definition in steps:
        if not isinstance(definition, dict) or "run" not in definition:
            raise ValueError(f"Step '{step_id}' is missing a 'run:' reference")
        run_value = definition["run"]
        if isinstance(run_value, str):
            external_refs.append(run_value)
        elif isinstance(run_value, dict):
            if run_value.get("class") != "CommandLineTool":
                unsupported_inline_steps.append(step_id)
        else:
            raise ValueError(f"Step '{step_id}' has an invalid 'run:' value")

    return WorkflowOverview(
        name=doc.get("label"),
        step_count=len(steps),
        external_refs=external_refs,
        unsupported_inline_steps=unsupported_inline_steps,
        cwl_version=doc.get("cwlVersion"),
    )


def extract_inline_components(cwl_content: str) -> list[ExtractedComponent]:
    """Extracts every step's inline `run: {class: CommandLineTool, ...}` as a standalone
    tool document. Steps with an external (filename) `run:`, or an inline `run:` that
    isn't a CommandLineTool, are silently skipped - callers that need those read
    read_workflow_overview's external_refs / unsupported_inline_steps instead.

    Raises ValueError if the document is not a valid CWL Workflow.
    """
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError as err:
        raise ValueError(f"YAML parse error: {err}") from err

    if not isinstance(doc, dict):
        raise ValueError("CWL document must be a mapping")
    if doc.get("class") != "Workflow":
        raise ValueError(f"class is '{doc.get('class')}', expected 'Workflow'")

    steps = normalize_steps(doc.get("steps"))

    components: list[ExtractedComponent] = []
    for step_id, definition in steps:
        run_value = definition.get("run") if isinstance(definition, dict) else None
        if not isinstance(run_value, dict) or run_value.get("class") != "CommandLineTool":
            continue

        cwl_text = yaml.dump(run_value, default_flow_style=False, sort_keys=False, allow_unicode=True)

        raw_inputs = run_value.get("inputs") or {}
        raw_outputs = run_value.get("outputs") or {}
        components.append(
            ExtractedComponent(
                step_id=step_id,
                suggested_name=_step_id_to_name(step_id),
                cwl_content=cwl_text,
                description=run_value.get("doc"),
                inputs=list(raw_inputs.values()) if isinstance(raw_inputs, dict) else list(raw_inputs),
                outputs=list(raw_outputs.values()) if isinstance(raw_outputs, dict) else list(raw_outputs),
            )
        )
    return components


def extract_step_definitions(cwl_content: str) -> list[tuple[str, dict]]:
    """Steps of a `class: Workflow` document in declaration order, tolerant of inline
    `run:` mappings (unlike extract_workflow_steps, which is strict-external-only and
    stays reserved for the zip-upload/Builder-sync path). Callers are expected to have
    already validated the document is a Workflow (e.g. via read_workflow_overview) -
    this re-parses independently, matching this module's existing per-function reparse
    convention, and only raises ValueError for YAML/steps-shape problems.
    """
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError as err:
        raise ValueError(f"YAML parse error: {err}") from err
    return normalize_steps(doc.get("steps") if isinstance(doc, dict) else None)


def externalize_inline_steps(cwl_content: str, run_references: dict[str, str]) -> str:
    """Rewrites a self-contained/mixed Workflow document so each inline CommandLineTool
    step named in `run_references` (step_id -> new filename) points at that filename
    instead of embedding the tool inline. The tool now lives in its own persisted
    Component, so the stored pipeline must reference it exactly like every other step
    (external-ref or Builder-generated) already does - this is what keeps
    WorkflowStep.run_reference true to "what the pipeline's run: lines point at", the
    invariant get_download/assemble_cwl_zip already relies on. Steps not present in
    `run_references` (already-external, or none) are left untouched. normalize_steps
    returns references to the *same* nested dict objects inside `doc`, not copies, so
    mutating `definition["run"]` here mutates `doc` directly - no need to rebuild
    `steps:`.
    """
    doc: Any = load_cwl(cwl_content)
    for step_id, definition in normalize_steps(doc.get("steps")):
        if step_id in run_references:
            definition["run"] = run_references[step_id]
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)
