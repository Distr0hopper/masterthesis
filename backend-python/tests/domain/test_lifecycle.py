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
    can_bind,
    can_publish,
    confirm_step,
    is_public,
    mark_deprecated,
    mark_draft,
    mark_published,
    mark_undeprecated,
    retract_impact,
    unbind_step,
)
from app.domain.models.component import Component, ComponentKind, ComponentStatus
from app.domain.models.tool import Tool
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep

ME = uuid.uuid4()
THEM = uuid.uuid4()
DRAFT, PUBLISHED, DEPRECATED = ComponentStatus.DRAFT, ComponentStatus.PUBLISHED, ComponentStatus.DEPRECATED
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


def move(component: Component, target: ComponentStatus) -> None:
    match target:
        case ComponentStatus.PUBLISHED:
            mark_published([component])
        case ComponentStatus.DRAFT:
            mark_draft([component])
        case ComponentStatus.DEPRECATED:
            mark_deprecated(component, "superseded")


LEGAL = {
    (DRAFT, DRAFT), (DRAFT, PUBLISHED),
    (PUBLISHED, PUBLISHED), (PUBLISHED, DRAFT), (PUBLISHED, DEPRECATED),
    (DEPRECATED, DEPRECATED), (DEPRECATED, PUBLISHED),
}  # fmt: skip
ALL_EDGES = [(a, b) for a in ComponentStatus for b in ComponentStatus]


@pytest.mark.parametrize(("current", "target"), ALL_EDGES)
def test_the_status_table_decides_every_edge(current: ComponentStatus, target: ComponentStatus) -> None:
    component = tool("t", current)
    if (current, target) in LEGAL:
        move(component, target)
        assert component.status == target
    else:
        with pytest.raises(IllegalStatusTransitionError):
            move(component, target)
        assert component.status == current


def test_a_deprecated_version_never_goes_straight_back_to_draft() -> None:
    component = tool("t", DEPRECATED)
    with pytest.raises(IllegalStatusTransitionError, match="published"):
        mark_draft([component])
    assert component.status == DEPRECATED


def test_the_note_lives_and_dies_with_the_deprecated_status() -> None:
    component = tool("t", PUBLISHED)
    mark_deprecated(component, "wrong CRS handling, use v3")
    assert (component.status, component.deprecation_note) == (DEPRECATED, "wrong CRS handling, use v3")
    mark_deprecated(component, "use v4")
    assert component.deprecation_note == "use v4"
    mark_undeprecated(component)
    assert (component.status, component.deprecation_note) == (PUBLISHED, None)


def test_only_a_deprecated_version_can_be_undeprecated() -> None:
    with pytest.raises(IllegalStatusTransitionError):
        mark_undeprecated(tool("t", PUBLISHED))


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
    public = tool("public", PUBLISHED)
    check = can_publish(workflow("root", public, tool("draft", DRAFT)), ME)
    assert [c.name for c in check.own_drafts] == ["draft"]


def test_publishing_a_parent_never_touches_a_deprecated_child() -> None:
    # drafts are `== DRAFT`, never "not published" - otherwise the deprecated child would
    # land in own_drafts and mark_published would silently un-deprecate it
    old = tool("old", DEPRECATED)
    old.deprecation_note = "use v2"
    nested = workflow("nested", old, status=PUBLISHED, owner=THEM)
    root = workflow("root", nested, tool("draft", DRAFT))

    check = can_publish(root, ME)
    mark_published([*check.own_drafts, root])

    assert old not in check.own_drafts
    assert (old.status, old.deprecation_note) == (DEPRECATED, "use v2")


# --- deprecated versions under a publish -----------------------------------------------


@pytest.mark.parametrize("owner", [ME, THEM])
def test_a_deprecated_direct_child_blocks_whoever_owns_it(owner: uuid.UUID) -> None:
    old = tool("old", DEPRECATED, owner=owner)
    check = can_publish(workflow("root", old, tool("fine")), ME)
    assert check.deprecated_children == [old]


def test_a_deprecated_child_of_an_own_draft_going_public_along_blocks() -> None:
    old = tool("old", DEPRECATED, owner=THEM)
    inner = workflow("inner", old)  # my draft - it would go public with root
    check = can_publish(workflow("root", inner), ME)
    assert check.deprecated_children == [old]


def test_a_deprecated_version_below_an_already_public_workflow_does_not_block() -> None:
    # C publishes W0, which runs B's published W1, which runs A's since-deprecated T: W1's
    # dependency on T is old and not C's to fix - C only adds a dependent to W1
    t = tool("t", DEPRECATED, owner=uuid.uuid4())
    w1 = workflow("w1", t, status=PUBLISHED, owner=THEM)
    check = can_publish(workflow("w0", w1), ME)
    assert check.deprecated_children == []
    assert check.foreign_drafts == [] and check.own_drafts == []


# --- binding a new step -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("status", "owner", "bindable"),
    [
        (PUBLISHED, ME, True),
        (PUBLISHED, THEM, True),
        (DRAFT, ME, True),
        (DRAFT, THEM, False),
        (DEPRECATED, ME, False),
        (DEPRECATED, THEM, False),
    ],
)
def test_who_may_bind_what(status: ComponentStatus, owner: uuid.UUID, bindable: bool) -> None:
    assert can_bind(tool("t", status, owner=owner), ME) is bindable


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


def test_own_deprecated_ancestors_get_their_own_blocking_bucket() -> None:
    published = workflow("published", status=PUBLISHED)
    deprecated = workflow("deprecated", status=DEPRECATED)

    impact = retract_impact([published, deprecated], ME)

    assert [a.name for a in impact.own] == ["published"]
    assert [a.name for a in impact.own_deprecated] == ["deprecated"]
    assert impact.foreign == [] and impact.blocked


def test_a_foreign_deprecated_ancestor_blocks_like_any_foreign_one() -> None:
    impact = retract_impact([workflow("theirs", status=DEPRECATED, owner=THEM)], ME)
    assert [a.name for a in impact.foreign] == ["theirs"] and impact.blocked


def test_public_means_published_or_deprecated() -> None:
    assert is_public(tool("t", PUBLISHED)) and is_public(tool("t", DEPRECATED)) and not is_public(tool("t", DRAFT))
