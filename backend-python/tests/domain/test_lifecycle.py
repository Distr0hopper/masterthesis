"""The composite's lifecycles: both transition tables, and the publication invariant in
both directions - publishing a tree, and taking a version out of public view."""

import uuid

import pytest

from app.domain.composite.lifecycle import (
    COMPONENT_TRANSITIONS,
    STEP_TRANSITIONS,
    IllegalStatusTransitionError,
    IllegalStepTransitionError,
    bind_step,
    can_publish,
    confirm_step,
    is_public,
    mark_draft,
    mark_published,
    retract_impact,
    unbind_step,
)
from app.domain.models.component import Component, ComponentKind, ComponentStatus
from app.domain.models.tool import Tool
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep

ME = uuid.uuid4()
THEM = uuid.uuid4()
DRAFT, PUBLISHED = ComponentStatus.DRAFT, ComponentStatus.PUBLISHED
UNMATCHED, SUGGESTED, CONFIRMED, INLINE = (
    StepMatchStatus.UNMATCHED,
    StepMatchStatus.SUGGESTED,
    StepMatchStatus.CONFIRMED,
    StepMatchStatus.INLINE,
)


def tool(name: str, status: ComponentStatus = PUBLISHED, owner: uuid.UUID = ME) -> Component:
    component = Component(
        id=uuid.uuid4(), kind=ComponentKind.TOOL, name=name, cwl_content="", status=status, created_by_id=owner
    )
    component.tool = Tool()
    return component


def workflow(
    name: str,
    *children: Component,
    status: ComponentStatus = DRAFT,
    owner: uuid.UUID = ME,
    step_status: StepMatchStatus = CONFIRMED,
) -> Component:
    component = Component(
        id=uuid.uuid4(), kind=ComponentKind.WORKFLOW, name=name, cwl_content="", status=status, created_by_id=owner
    )
    component.workflow = Workflow(
        steps=[
            WorkflowStep(
                id=uuid.uuid4(),
                step_id=f"s{i}",
                run_reference=f"{c.name}.cwl",
                step_order=i,
                component_id=c.id,
                component=c,
                match_status=step_status,
            )
            for i, c in enumerate(children)
        ]
    )
    return component


def step(status: StepMatchStatus, bound: bool = True) -> WorkflowStep:
    child = tool("child")
    return WorkflowStep(
        id=uuid.uuid4(),
        step_id="s",
        run_reference="child.cwl",
        step_order=0,
        component_id=child.id if bound else None,
        component=child if bound else None,
        match_status=status,
        match_score=0.8,
    )


# --- the component status table --------------------------------------------------------


@pytest.mark.parametrize(
    ("current", "target"),
    [(DRAFT, DRAFT), (DRAFT, PUBLISHED), (PUBLISHED, PUBLISHED), (PUBLISHED, DRAFT)],
)
def test_component_status_edges_in_the_table_are_legal(current: ComponentStatus, target: ComponentStatus) -> None:
    component = tool("t", current)
    (mark_published if target == PUBLISHED else mark_draft)([component])
    assert component.status == target


def test_a_status_edge_missing_from_the_table_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    # stands in for the DEPRECATED ticket's missing DEPRECATED -> DRAFT edge
    monkeypatch.setitem(COMPONENT_TRANSITIONS, PUBLISHED, frozenset({PUBLISHED}))
    component = tool("t", PUBLISHED)
    with pytest.raises(IllegalStatusTransitionError):
        mark_draft([component])
    assert component.status == PUBLISHED


def test_every_status_has_a_row_in_the_table() -> None:
    assert set(COMPONENT_TRANSITIONS) == set(ComponentStatus)


# --- the step table ---------------------------------------------------------------------


def test_every_step_status_has_a_row_in_the_table() -> None:
    assert set(STEP_TRANSITIONS) == set(StepMatchStatus)


@pytest.mark.parametrize("current", [UNMATCHED, SUGGESTED, CONFIRMED])
def test_binding_suggests_and_clears_the_score(current: StepMatchStatus) -> None:
    s, other = step(current, bound=current != UNMATCHED), tool("other")
    bind_step(s, other)
    assert (s.match_status, s.component_id, s.component, s.match_score) == (SUGGESTED, other.id, other, None)


@pytest.mark.parametrize("current", [UNMATCHED, SUGGESTED, CONFIRMED])
def test_unbinding_clears_the_step(current: StepMatchStatus) -> None:
    s = step(current, bound=current != UNMATCHED)
    unbind_step(s)
    assert (s.match_status, s.component_id, s.component, s.match_score) == (UNMATCHED, None, None, None)


def test_clearing_an_already_empty_step_is_a_no_op_not_an_error() -> None:
    s = step(UNMATCHED, bound=False)
    unbind_step(s)
    assert s.match_status == UNMATCHED


@pytest.mark.parametrize("current", [SUGGESTED, CONFIRMED])
def test_a_bound_step_can_be_confirmed(current: StepMatchStatus) -> None:
    s = step(current)
    confirm_step(s)
    assert s.match_status == CONFIRMED


def test_an_unbound_step_cannot_be_confirmed() -> None:
    with pytest.raises(IllegalStepTransitionError):
        confirm_step(step(UNMATCHED, bound=False))


@pytest.mark.parametrize("move", [lambda s: bind_step(s, tool("x")), unbind_step, confirm_step])
def test_an_inline_step_never_moves(move) -> None:
    s = step(INLINE, bound=False)
    with pytest.raises(IllegalStepTransitionError):
        move(s)
    assert s.match_status == INLINE


# --- publishing a tree ------------------------------------------------------------------


def test_a_tool_has_nothing_in_its_way() -> None:
    check = can_publish(tool("t", DRAFT), ME)
    assert not check.root_unsettled and not check.own_drafts and not check.foreign_drafts


def test_publishing_checks_the_whole_tree() -> None:
    mine, theirs = tool("mine", DRAFT), tool("theirs", DRAFT, owner=THEM)
    inner = workflow("inner", mine, theirs, step_status=SUGGESTED)
    root = workflow("root", tool("public"), inner, step_status=CONFIRMED)

    check = can_publish(root, ME)

    assert not check.root_unsettled
    assert check.unsettled_nested == ["inner"]
    assert check.foreign_drafts == ["theirs"]
    assert {c.name for c in check.own_drafts} == {"inner", "mine"}


def test_only_drafts_are_published_along() -> None:
    # drafts are `== DRAFT`, never "not published" - a child in any other non-draft status
    # (e.g. a later DEPRECATED) must not be swept up and silently changed by its parent
    public = tool("public", PUBLISHED)
    check = can_publish(workflow("root", public, tool("draft", DRAFT)), ME)
    assert [c.name for c in check.own_drafts] == ["draft"]


def test_unsettled_root_is_reported() -> None:
    assert can_publish(workflow("root", tool("t"), step_status=UNMATCHED), ME).root_unsettled


def test_inline_steps_count_as_settled() -> None:
    assert not can_publish(workflow("root", tool("t"), step_status=INLINE), ME).root_unsettled


# --- taking a version out of public view ------------------------------------------------


def test_retract_splits_public_ancestors_by_owner_and_ignores_drafts() -> None:
    own_parent = workflow("a-own", status=PUBLISHED)
    own_grandparent = workflow("b-own", status=PUBLISHED)
    foreign = workflow("theirs", status=PUBLISHED, owner=THEM)
    private = workflow("private", status=DRAFT, owner=THEM)

    impact = retract_impact([own_grandparent, foreign, private, own_parent], ME)

    assert [a.name for a in impact.own] == ["a-own", "b-own"]
    assert [a.name for a in impact.foreign] == ["theirs"]
    assert impact.blocked


def test_retract_without_public_ancestors_is_free() -> None:
    impact = retract_impact([workflow("draft", status=DRAFT)], ME)
    assert impact.own == impact.foreign == [] and not impact.blocked


def test_public_means_the_public_statuses_not_just_published() -> None:
    assert is_public(tool("t", PUBLISHED)) and not is_public(tool("t", DRAFT))


# DEPRECATED ticket: add
# - publishing a parent never touches a DEPRECATED child (it isn't in own_drafts);
# - a DEPRECATED ancestor blocks a retract (it is in PUBLIC_STATUSES).
