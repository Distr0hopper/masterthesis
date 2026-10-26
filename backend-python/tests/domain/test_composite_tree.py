import uuid

import pytest

from app.domain.composite.tree import (
    ArchiveLayout,
    ConflictingTreeFileError,
    descendants,
    has_nested_workflows,
    leaf_tools,
    walk,
    would_create_cycle,
)
from app.domain.models.component import Component, ComponentKind
from app.domain.models.component_file import ComponentFile
from app.domain.models.tool import Tool
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep


def tool(name: str, cwl: str | None = None, files: dict[str, str] | None = None) -> Component:
    component = Component(
        id=uuid.uuid4(), kind=ComponentKind.TOOL, name=name, cwl_content=cwl or f"class: CommandLineTool # {name}"
    )
    component.tool = Tool()
    component.files = [ComponentFile(path=p, content=c) for p, c in (files or {}).items()]
    return component


def workflow(name: str, *children: Component | None, version: int = 1) -> Component:
    component = Component(
        id=uuid.uuid4(),
        kind=ComponentKind.WORKFLOW,
        name=name,
        version=version,
        cwl_content=f"class: Workflow # {name}",
    )
    component.workflow = Workflow(
        steps=[
            WorkflowStep(
                step_id=f"step_{i}",
                run_reference=f"{child.name}.cwl" if child is not None else "missing.cwl",
                step_order=i,
                component=child,
                match_status=StepMatchStatus.CONFIRMED if child is not None else StepMatchStatus.UNMATCHED,
            )
            for i, child in enumerate(children)
        ]
    )
    return component


def test_a_tool_is_a_leaf() -> None:
    leaf = tool("t")
    assert leaf.children == []
    assert list(walk(leaf)) == [leaf]
    assert leaf_tools(leaf) == [leaf]


def test_walk_visits_parents_before_children_and_each_component_once() -> None:
    shared = tool("shared")
    inner = workflow("inner", shared, tool("only-inner"))
    outer = workflow("outer", tool("first"), inner, shared)

    assert [c.name for c in walk(outer)] == ["outer", "first", "inner", "shared", "only-inner"]
    assert [c.name for c in descendants(outer)] == ["first", "inner", "shared", "only-inner"]
    assert sorted(c.name for c in leaf_tools(outer)) == ["first", "only-inner", "shared"]


def test_unbound_steps_are_skipped() -> None:
    assert workflow("w", None, tool("t")).children[0].name == "t"


def test_nesting_a_workflow_into_itself_is_a_cycle() -> None:
    parent = workflow("pipeline")
    assert would_create_cycle(parent, parent)


def test_nesting_another_version_of_the_same_lineage_is_a_cycle() -> None:
    v1 = workflow("pipeline", version=1)
    v2 = workflow("pipeline", version=2)
    assert would_create_cycle(v1, v2)


def test_indirect_self_reference_is_a_cycle() -> None:
    parent = workflow("outer")
    child = workflow("middle", workflow("inner", workflow("outer", version=3)))
    assert would_create_cycle(parent, child)


def test_unrelated_nesting_is_not_a_cycle() -> None:
    assert not would_create_cycle(workflow("outer"), workflow("inner", tool("outer-ish")))
    assert not would_create_cycle(workflow("outer"), tool("t"))


def test_each_nested_workflow_gets_a_folder_of_its_own() -> None:
    inner = workflow("inner", tool("b"), workflow("deepest", tool("c")))
    outer = workflow("outer", tool("a"), inner)

    layout = ArchiveLayout.of(outer)

    assert sorted(layout.documents) == [
        "a.cwl",
        "inner/b.cwl",
        "inner/deepest/c.cwl",
        "inner/deepest/deepest.cwl",
        "inner/inner.cwl",
    ]
    assert layout.documents["inner/inner.cwl"] is inner
    # only the steps running a nested workflow move - relative to the document running them
    assert layout.retargets == {"": {"step_1": "inner/inner.cwl"}, "inner/inner.cwl": {"step_1": "deepest/deepest.cwl"}}


def test_two_versions_of_one_tool_fit_when_a_nested_workflow_runs_the_other() -> None:
    # what superseding produces: the parent moved on to v2, the nested workflow still runs v1
    outer = workflow("outer", tool("a", cwl="v2"), workflow("inner", tool("a", cwl="v1")))

    documents = {path: c.cwl_content for path, c in ArchiveLayout.of(outer).documents.items()}

    assert (documents["a.cwl"], documents["inner/a.cwl"]) == ("v2", "v1")


def test_a_component_reached_twice_is_written_once() -> None:
    shared = tool("a")
    assert sorted(ArchiveLayout.of(workflow("outer", shared, shared)).documents) == ["a.cwl"]


def test_one_pipeline_cannot_run_two_documents_under_one_name() -> None:
    outer = workflow("outer", tool("a", cwl="one"), tool("a", cwl="two"))
    with pytest.raises(ConflictingTreeFileError) as raised:
        ArchiveLayout.of(outer)
    assert (raised.value.path, raised.value.imported) == ("a.cwl", False)


def test_imports_sit_next_to_the_document_importing_them() -> None:
    types = {"types/spatial.yml": "x"}
    outer = workflow("outer", tool("a", files=types), tool("b", files=types), workflow("inner", tool("c", files=types)))
    assert ArchiveLayout.of(outer).imported == {"types/spatial.yml": "x", "inner/types/spatial.yml": "x"}

    clashing = workflow("outer", tool("a", files=types), tool("b", files={"types/spatial.yml": "y"}))
    with pytest.raises(ConflictingTreeFileError) as raised:
        ArchiveLayout.of(clashing)
    assert raised.value.imported


def test_nested_workflows_are_detected() -> None:
    assert not has_nested_workflows(workflow("flat", tool("a")))
    assert has_nested_workflows(workflow("outer", workflow("inner", tool("a"))))
