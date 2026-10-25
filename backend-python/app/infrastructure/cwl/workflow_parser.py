import posixpath
import re
from dataclasses import dataclass
from typing import Any

import yaml  # dump only - reads go through load_cwl (PyYAML rejects valid CWL v1.2 flow scalars)

from app.infrastructure.cwl.yaml_io import YAMLError, load_cwl


def is_workflow_cwl(cwl_content: str) -> bool:
    try:
        doc: Any = load_cwl(cwl_content)
    except YAMLError:
        return False
    return isinstance(doc, dict) and doc.get("class") == "Workflow"


def match_archive_path(target: str, files: dict[str, str]) -> str | None:
    """The archive entry `target` refers to, tolerating layout differences: exactly, else
    the one entry ending in it, else the one entry with its file name."""
    if target in files:
        return target
    suffix = "/" + target
    matches = [path for path in files if path.endswith(suffix)]
    if len(matches) == 1:
        return matches[0]
    # last resort: the reference writes a path the archive flattened (or vice versa)
    base = target.rsplit("/", 1)[-1]
    matches = [path for path in files if path.rsplit("/", 1)[-1] == base]
    return matches[0] if len(matches) == 1 else None


def resolve_run_reference(reference: str, document: str, files: dict[str, str]) -> str | None:
    """The archive file a `run:` in `document` points at. CWL resolves it relative to the
    referencing document - `cwl/a.cwl` running `b.cwl` means `cwl/b.cwl`."""
    resolved = posixpath.normpath(posixpath.join(posixpath.dirname(document), reference))
    if resolved in files:
        return resolved
    return match_archive_path(reference, files)


def _string_runs(cwl_content: str) -> list[str]:
    """The `run:` filenames of a Workflow document - [] for anything else or unreadable."""
    try:
        doc: Any = load_cwl(cwl_content)
        steps = normalize_steps(doc.get("steps")) if isinstance(doc, dict) else []
    except (YAMLError, ValueError):
        return []
    return [d["run"] for _, d in steps if isinstance(d, dict) and isinstance(d.get("run"), str)]


@dataclass(frozen=True)
class ArchiveRoot:
    filename: str
    content: str
    #: Workflow files the root never runs, at any depth - left out of the upload
    unused_workflows: list[str]


def find_root_workflow(files: dict[str, str]) -> ArchiveRoot:
    """The archive's main pipeline: the `class: Workflow` file no other workflow runs.

    Identified by content, not filename, since the user may name it anything. Nested
    workflows are the ones some `run:` points at. Should several be run by nobody, the one
    nearest the archive's top wins if that is unambiguous - the others are reported as
    unused. Raises ValueError for no workflow, or no unambiguous root.
    """
    workflows = sorted(name for name, content in files.items() if is_workflow_cwl(content))
    if not workflows:
        raise ValueError("No CWL file with class: Workflow found in the archive")

    referenced = {
        resolve_run_reference(run, name, files) for name in workflows for run in _string_runs(files[name])
    }
    roots = [name for name in workflows if name not in referenced]
    if not roots:
        raise ValueError(f"The workflows in the archive all run each other ({', '.join(workflows)}); none is the root")
    shallowest = min(name.count("/") for name in roots)
    top = [name for name in roots if name.count("/") == shallowest]
    if len(top) > 1:
        raise ValueError(
            f"Multiple CWL files with class: Workflow that no other workflow runs ({', '.join(top)}); "
            "expected exactly one root workflow"
        )

    root = top[0]
    reachable = {root} | {step.target for step in walk_archive_steps(root, files) if step.target is not None}
    return ArchiveRoot(
        filename=root,
        content=files[root],
        unused_workflows=[name for name in workflows if name not in reachable],
    )


@dataclass(frozen=True)
class ArchiveStep:
    """One step of an uploaded workflow tree, as it occurs - a sub-workflow run by two steps
    contributes its steps twice, under two paths."""

    #: step ids from the root down - `graph_generation/generate_graph`
    path: str
    #: the archive file declaring the step
    document: str
    step_id: str
    definition: dict
    #: the archive file a `run:` filename resolves to - None for an inline `run:`, or a
    #: filename the archive does not hold
    target: str | None

    @property
    def parent_path(self) -> str | None:
        return self.path.rpartition("/")[0] or None


def walk_archive_steps(root: str, files: dict[str, str]) -> list[ArchiveStep]:
    """Every step of the tree below the `root` file, depth-first, a parent before the steps
    of the workflow it runs. Raises ValueError for a document without readable steps, or for
    workflows that run each other in a cycle."""
    result: list[ArchiveStep] = []

    def visit(document: str, prefix: str, stack: tuple[str, ...]) -> None:
        try:
            doc: Any = load_cwl(files[document])
        except YAMLError as err:
            raise ValueError(f"{document}: YAML parse error: {err}") from err
        try:
            steps = normalize_steps(doc.get("steps") if isinstance(doc, dict) else None)
        except ValueError as err:
            raise ValueError(f"{document}: {err}") from err

        for step_id, definition in steps:
            run_value = definition.get("run") if isinstance(definition, dict) else None
            if run_value is None:
                raise ValueError(f"{document}: step '{step_id}' is missing a 'run:' reference")
            target = resolve_run_reference(run_value, document, files) if isinstance(run_value, str) else None
            step = ArchiveStep(f"{prefix}{step_id}", document, step_id, definition, target)
            result.append(step)
            if target is None or not is_workflow_cwl(files[target]):
                continue
            if target in stack:
                raise ValueError(f"Workflows run each other in a cycle: {' -> '.join((*stack, target))}")
            visit(target, f"{step.path}/", (*stack, target))

    visit(root, "", (root,))
    return result


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
    #: step ids whose `run:` is an inline mapping but not `class: CommandLineTool` (e.g.
    #: an inline ExpressionTool or sub-Workflow). These are glue, not reusable tools, so
    #: they stay embedded in the pipeline rather than becoming Components - not returned
    #: by extract_inline_components and not a filename either, so callers need this to
    #: know step_count still accounts for them.
    inline_only_steps: list[str]
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

    Raises ValueError for anything that is not a readable `class: Workflow` with steps,
    but does NOT reject inline `run:` mappings - step_count always comes from an independent len(steps), never derived by summing
    external_refs/extracted-components counts, since a step whose inline `run:` isn't a
    CommandLineTool (see inline_only_steps) would otherwise silently vanish from
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
    inline_only_steps: list[str] = []
    for step_id, definition in steps:
        if not isinstance(definition, dict) or "run" not in definition:
            raise ValueError(f"Step '{step_id}' is missing a 'run:' reference")
        run_value = definition["run"]
        if isinstance(run_value, str):
            external_refs.append(run_value)
        elif isinstance(run_value, dict):
            if run_value.get("class") != "CommandLineTool":
                inline_only_steps.append(step_id)
        else:
            raise ValueError(f"Step '{step_id}' has an invalid 'run:' value")

    return WorkflowOverview(
        name=doc.get("label"),
        step_count=len(steps),
        external_refs=external_refs,
        inline_only_steps=inline_only_steps,
        cwl_version=doc.get("cwlVersion"),
    )


#: top-level-only CWL directives an extracted inline tool inherits from its parent
_DOCUMENT_LEVEL_KEYS = ("$namespaces", "$schemas")


def extract_inline_components(cwl_content: str) -> list[ExtractedComponent]:
    """Extracts every step's inline `run: {class: CommandLineTool, ...}` as a standalone
    tool document. Steps with an external (filename) `run:`, or an inline `run:` that
    isn't a CommandLineTool, are silently skipped - callers that need those read
    read_workflow_overview's external_refs / inline_only_steps instead.

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

        # $namespaces/$schemas are only allowed on the top-level document, so an inline tool
        # relies on its parent's - carry them over, or the standalone tool's `format`
        # prefixes (eo:GeoTIFF) no longer expand and can't be resolved to a label
        for key in _DOCUMENT_LEVEL_KEYS:
            if key in doc and key not in run_value:
                run_value = {**run_value, key: doc[key]}

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
    `run:` mappings. Callers are expected to have
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
