"""Reading an uploaded workflow: finding the pipeline in the archive, both forms of
`steps:`, inline tools pulled out as their own documents, and matching step references
to existing components by name."""

import uuid

import pytest
import yaml

from app.infrastructure.cwl.cwl_matcher import MATCH_THRESHOLD, best_match, normalize_name
from app.infrastructure.cwl.workflow_parser import (
    externalize_inline_steps,
    extract_inline_components,
    extract_step_definitions,
    find_root_workflow,
    is_self_contained,
    is_workflow_cwl,
    normalize_steps,
    read_workflow_overview,
    resolve_run_reference,
    walk_archive_steps,
)

TOOL = "cwlVersion: v1.2\nclass: CommandLineTool\nbaseCommand: [echo]\ninputs: {}\noutputs: {}\n"

EXTERNAL = """\
cwlVersion: v1.2
class: Workflow
label: Track cleaning
inputs: {}
outputs: {}
steps:
  step_remove_outliers:
    run: remove-outliers.cwl
    in: {}
    out: []
  step_filter:
    run: filter.cwl
    in: {}
    out: []
"""

SELF_CONTAINED = """\
cwlVersion: v1.2
class: Workflow
$namespaces:
  eo: https://dfg-sos.github.io/ontologies/eo-formats#
$schemas:
  - https://dfg-sos.github.io/ontologies/eo-formats.owl
inputs: {}
outputs: {}
steps:
  step_Remove_Outliers:
    run:
      class: CommandLineTool
      doc: Drops implausible fixes
      baseCommand: [Rscript]
      inputs:
        tracks: {type: File, format: eo:GeoJSON}
      outputs:
        cleaned: {type: File}
    in: {}
    out: [cleaned]
  glue:
    run:
      class: ExpressionTool
      expression: "$({})"
      inputs: {}
      outputs: {}
    in: {}
    out: []
  step_filter:
    run: filter.cwl
    in: {}
    out: []
"""


def test_the_pipeline_is_found_by_its_class_not_its_filename() -> None:
    files = {"a.cwl": TOOL, "anything-goes.cwl": EXTERNAL, "notes.txt": "not: [yaml"}
    root = find_root_workflow(files)
    assert (root.filename, root.content, root.unused_workflows) == ("anything-goes.cwl", EXTERNAL, [])


def test_an_archive_without_a_workflow_is_refused() -> None:
    with pytest.raises(ValueError, match="No CWL file"):
        find_root_workflow({"a.cwl": TOOL})


def test_an_archive_with_two_unrelated_workflows_names_both() -> None:
    with pytest.raises(ValueError, match="one.cwl, two.cwl"):
        find_root_workflow({"one.cwl": EXTERNAL, "two.cwl": EXTERNAL})


def workflow_running(*runs: str) -> str:
    steps = "".join(f"  s{i}:\n    run: {run}\n    in: {{}}\n    out: []\n" for i, run in enumerate(runs))
    return f"cwlVersion: v1.2\nclass: Workflow\ninputs: {{}}\noutputs: {{}}\nsteps:\n{steps}"


#: the shape of the Africapolis archive: the root runs `cwl/...`, the nested workflows run
#: their siblings relative to themselves, and one nested workflow is run by nobody
NESTED_ARCHIVE = {
    "Root.cwl": workflow_running("cwl/Inner.cwl", "cwl/tool.cwl"),
    "cwl/Inner.cwl": workflow_running("tool.cwl", "Deeper.cwl"),
    "cwl/Deeper.cwl": workflow_running("tool.cwl"),
    "cwl/Orphan.cwl": workflow_running("tool.cwl"),
    "cwl/tool.cwl": TOOL,
}


def test_the_root_is_the_workflow_no_other_one_runs_the_top_most_if_several() -> None:
    root = find_root_workflow(NESTED_ARCHIVE)
    assert (root.filename, root.unused_workflows) == ("Root.cwl", ["cwl/Orphan.cwl"])


def test_workflows_running_each_other_have_no_root() -> None:
    with pytest.raises(ValueError, match="none is the root"):
        find_root_workflow({"a.cwl": workflow_running("b.cwl"), "b.cwl": workflow_running("a.cwl")})


def test_a_run_reference_resolves_relative_to_its_document() -> None:
    assert resolve_run_reference("tool.cwl", "cwl/Inner.cwl", NESTED_ARCHIVE) == "cwl/tool.cwl"
    assert resolve_run_reference("cwl/tool.cwl", "Root.cwl", NESTED_ARCHIVE) == "cwl/tool.cwl"
    # tolerated: a flattened reference to the one file of that name
    assert resolve_run_reference("Deeper.cwl", "Root.cwl", NESTED_ARCHIVE) == "cwl/Deeper.cwl"
    assert resolve_run_reference("missing.cwl", "Root.cwl", NESTED_ARCHIVE) is None


def test_the_walk_visits_every_step_occurrence_parents_first() -> None:
    steps = walk_archive_steps("Root.cwl", NESTED_ARCHIVE)
    assert [(s.path, s.target) for s in steps] == [
        ("s0", "cwl/Inner.cwl"),
        ("s0/s0", "cwl/tool.cwl"),
        ("s0/s1", "cwl/Deeper.cwl"),
        ("s0/s1/s0", "cwl/tool.cwl"),
        ("s1", "cwl/tool.cwl"),
    ]
    assert steps[3].parent_path == "s0/s1"


def test_the_walk_refuses_a_cycle_below_the_root() -> None:
    files = {
        "root.cwl": workflow_running("a.cwl"),
        "a.cwl": workflow_running("b.cwl"),
        "b.cwl": workflow_running("a.cwl"),
    }
    with pytest.raises(ValueError, match="cycle"):
        walk_archive_steps("root.cwl", files)


def test_unreadable_yaml_is_simply_not_a_workflow() -> None:
    assert not is_workflow_cwl("class: [Workflow")
    assert not is_workflow_cwl("- a list\n- not a mapping\n")


def test_idmap_and_list_steps_read_the_same_in_declaration_order() -> None:
    as_map = {"b": {"run": "b.cwl"}, "a": {"run": "a.cwl"}}
    as_list = [{"id": "b", "run": "b.cwl"}, {"id": "a", "run": "a.cwl"}]
    assert [step_id for step_id, _ in normalize_steps(as_map)] == ["b", "a"]
    assert [step_id for step_id, _ in normalize_steps(as_list)] == ["b", "a"]


@pytest.mark.parametrize("steps", [None, {}, []])
def test_a_workflow_without_steps_is_refused(steps: object) -> None:
    with pytest.raises(ValueError, match="no steps"):
        normalize_steps(steps)


def test_a_list_step_without_an_id_is_refused() -> None:
    with pytest.raises(ValueError, match="'id'"):
        normalize_steps([{"run": "a.cwl"}])


def test_the_overview_counts_every_step_including_inline_glue() -> None:
    overview = read_workflow_overview(SELF_CONTAINED)
    assert overview.step_count == 3
    assert overview.external_refs == ["filter.cwl"]
    assert overview.inline_only_steps == ["glue"]
    assert overview.cwl_version == "v1.2"


def test_the_overview_takes_the_label_as_name() -> None:
    overview = read_workflow_overview(EXTERNAL)
    assert overview.name == "Track cleaning"
    assert overview.external_refs == ["remove-outliers.cwl", "filter.cwl"]
    assert overview.inline_only_steps == []


def test_the_overview_refuses_a_tool_and_a_step_without_run() -> None:
    with pytest.raises(ValueError, match="expected 'Workflow'"):
        read_workflow_overview(TOOL)
    without_run = EXTERNAL.replace("    run: filter.cwl\n", "")
    with pytest.raises(ValueError, match="step_filter"):
        read_workflow_overview(without_run)


def test_only_an_inline_command_line_tool_makes_a_workflow_self_contained() -> None:
    assert is_self_contained(SELF_CONTAINED)
    assert not is_self_contained(EXTERNAL)
    assert not is_self_contained(TOOL)
    assert not is_self_contained("class: [Workflow")


def test_only_inline_command_line_tools_are_extracted() -> None:
    [component] = extract_inline_components(SELF_CONTAINED)
    assert component.step_id == "step_Remove_Outliers"
    assert component.suggested_name == "remove-outliers"
    assert component.description == "Drops implausible fixes"
    assert component.inputs == [{"type": "File", "format": "eo:GeoJSON"}]
    assert component.outputs == [{"type": "File"}]


def test_an_extracted_tool_carries_the_parents_namespaces_so_its_formats_still_expand() -> None:
    [component] = extract_inline_components(SELF_CONTAINED)
    tool = yaml.safe_load(component.cwl_content)
    assert tool["class"] == "CommandLineTool"
    assert tool["$namespaces"] == {"eo": "https://dfg-sos.github.io/ontologies/eo-formats#"}
    assert tool["$schemas"] == ["https://dfg-sos.github.io/ontologies/eo-formats.owl"]
    # inline tools inherit cwlVersion - the caller injects one before persisting
    assert "cwlVersion" not in tool


def test_externalizing_points_only_the_named_inline_steps_at_their_new_files() -> None:
    rewritten = externalize_inline_steps(SELF_CONTAINED, {"step_Remove_Outliers": "remove-outliers.cwl"})
    runs = {step_id: definition["run"] for step_id, definition in extract_step_definitions(rewritten)}
    assert runs["step_Remove_Outliers"] == "remove-outliers.cwl"
    assert runs["step_filter"] == "filter.cwl"
    assert runs["glue"]["class"] == "ExpressionTool"
    assert not is_self_contained(rewritten)
    assert read_workflow_overview(rewritten).step_count == 3


def test_spellings_of_one_name_normalise_alike() -> None:
    assert normalize_name("remove-outliers.cwl") == "remove-outliers"
    assert normalize_name("Remove_Outliers") == "remove-outliers"
    assert normalize_name("Remove Outliers.CWL") == "remove-outliers"


def test_the_closest_candidate_wins() -> None:
    exact, close = uuid.uuid4(), uuid.uuid4()
    match = best_match("remove-outliers.cwl", [(close, "remove-outlier"), (exact, "Remove_Outliers")])
    assert match is not None
    assert match[:2] == (exact, "Remove_Outliers")
    assert match[2] == 1.0


def test_nothing_close_enough_is_no_match() -> None:
    assert best_match("remove-outliers.cwl", [(uuid.uuid4(), "speed-filter")]) is None
    assert best_match("remove-outliers.cwl", []) is None


def test_a_tie_keeps_the_first_candidate() -> None:
    first, second = uuid.uuid4(), uuid.uuid4()
    match = best_match("filter", [(first, "Filter"), (second, "filter")])
    assert match is not None and match[0] == first
    assert match[2] >= MATCH_THRESHOLD
