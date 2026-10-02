import uuid

import pytest

from app.domain.composite.tree import (
    ConflictingTreeFileError,
    auxiliary_files,
    descendants,
    has_nested_workflows,
    leaf_tools,
    step_files,
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
        id=uuid.uuid4(), kind=ComponentKind.WORKFLOW, name=name, version=version, cwl_content=f"class: Workflow # {name}"
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


def test_step_files_include_nested_workflows_and_their_steps() -> None:
    inner = workflow("inner", tool("b"))
    outer = workflow("outer", tool("a"), inner)

    assert [name for name, _ in step_files(outer)] == ["a.cwl", "b.cwl", "inner.cwl"]
    assert dict(step_files(outer))["inner.cwl"] == inner.cwl_content


def test_step_files_reject_two_documents_under_one_name() -> None:
    outer = workflow("outer", tool("a", cwl="one"), workflow("inner", tool("a", cwl="two")))
    with pytest.raises(ConflictingTreeFileError):
        step_files(outer)


def test_auxiliary_files_merge_identical_imports_across_the_tree() -> None:
    types = {"types/spatial.yml": "x"}
    outer = workflow("outer", tool("a", files=types), workflow("inner", tool("b", files=types)))
    assert auxiliary_files(outer) == [("types/spatial.yml", "x")]

    outer = workflow("outer", tool("a", files=types), tool("b", files={"types/spatial.yml": "y"}))
    with pytest.raises(ConflictingTreeFileError):
        auxiliary_files(outer)


def test_nested_workflows_are_detected() -> None:
    assert not has_nested_workflows(workflow("flat", tool("a")))
    assert has_nested_workflows(workflow("outer", workflow("inner", tool("a"))))
