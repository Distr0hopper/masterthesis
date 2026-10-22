"""The two lifecycles of the composite - a component's status and a step's match status -
and the invariant tying them together across the tree:

    a public workflow only runs public components, and every one of its steps is settled.

The transition tables are the only definition of which changes are legal, and the
functions below are the only writers of `Component.status` and of a step's match.
Everything is pure, over already-loaded Components (see composite.tree): the services
load the tree or the ancestors first, then ask here what is allowed.

Three statuses, three questions - never answer one with another's check:
- a draft is `status == DRAFT` - never "not published", or a deprecated child would be
  taken for a draft and silently re-published along with its parent;
- "visible to everyone" is `is_public` (published or deprecated);
- "listed and offered for new use" is LISTED_STATUSES (published only).

A published version is a promise to others - they saw, ran, nested or cited it. So it can
only be taken back to a draft within a short window after it first went public (see
within_unpublish_window), and only drafts are ever deleted. After the window it stays public
for good: retracted, at most, by deprecating it. Changes always go into a new version - a
public version's content never changes.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.domain.composite.tree import descendants
from app.domain.models.component import Component, ComponentStatus
from app.domain.models.workflow_step import SETTLED_STEP_STATUSES, StepMatchStatus, WorkflowStep

COMPONENT_TRANSITIONS: dict[ComponentStatus, frozenset[ComponentStatus]] = {
    # idempotent / publish
    ComponentStatus.DRAFT: frozenset({ComponentStatus.DRAFT, ComponentStatus.PUBLISHED}),
    # idempotent / unpublish (see retract_impact) / deprecate
    ComponentStatus.PUBLISHED: frozenset(
        {ComponentStatus.PUBLISHED, ComponentStatus.DRAFT, ComponentStatus.DEPRECATED}
    ),
    # idempotent (a new note) / undeprecate. No way back to DRAFT: what still runs a
    # deprecated version would break, so it goes back through PUBLISHED and the retract rule
    ComponentStatus.DEPRECATED: frozenset({ComponentStatus.DEPRECATED, ComponentStatus.PUBLISHED}),
}

STEP_TRANSITIONS: dict[StepMatchStatus, frozenset[StepMatchStatus]] = {
    # bind / clearing an already empty step is a no-op, not an error
    StepMatchStatus.UNMATCHED: frozenset({StepMatchStatus.SUGGESTED, StepMatchStatus.UNMATCHED}),
    # rebind / confirm / clear
    StepMatchStatus.SUGGESTED: frozenset(
        {StepMatchStatus.SUGGESTED, StepMatchStatus.CONFIRMED, StepMatchStatus.UNMATCHED}
    ),
    # rebind / confirm again / clear, or the child is deleted
    StepMatchStatus.CONFIRMED: frozenset(
        {StepMatchStatus.SUGGESTED, StepMatchStatus.CONFIRMED, StepMatchStatus.UNMATCHED}
    ),
    # the definition lives inside the pipeline - there is never a component to bind
    StepMatchStatus.INLINE: frozenset(),
}

#: the statuses everyone can see - what a public workflow may run, and what a retract must not break
PUBLIC_STATUSES = frozenset({ComponentStatus.PUBLISHED, ComponentStatus.DEPRECATED})
#: the statuses listed (browse, search, latest, stats) and offered for new use (palette, picker)
LISTED_STATUSES = frozenset({ComponentStatus.PUBLISHED})


class IllegalStatusTransitionError(ValueError):
    def __init__(self, component: Component, target: ComponentStatus) -> None:
        self.component = component
        self.target = target
        allowed = sorted(s.value for s in COMPONENT_TRANSITIONS.get(ComponentStatus(component.status), ()) if s != component.status)
        super().__init__(
            f"'{component.name}' v{component.version} is {ComponentStatus(component.status).value} and cannot "
            f"become {target.value} - it can only become {' or '.join(allowed) or 'nothing else'}"
        )


class IllegalStepTransitionError(ValueError):
    def __init__(self, step: WorkflowStep, target: StepMatchStatus) -> None:
        super().__init__(f"Step '{step.step_id}' cannot go from {step.match_status} to {target}")


# --- component status ------------------------------------------------------------------


def is_public(component: Component) -> bool:
    return component.status in PUBLIC_STATUSES


def is_draft(component: Component) -> bool:
    return component.status == ComponentStatus.DRAFT


def unpublishable_until(component: Component, window: timedelta) -> datetime | None:
    """Until when the published version may still go back to a draft - None once it isn't
    published, or has no first publish recorded."""
    if component.status != ComponentStatus.PUBLISHED or component.first_published_at is None:
        return None
    return component.first_published_at + window


def within_unpublish_window(component: Component, now: datetime, window: timedelta) -> bool:
    """Whether the published version is still young enough to go back to a draft - an
    accidental publish is undone, anything older is only ever deprecated."""
    until = unpublishable_until(component, window)
    return until is not None and now <= until


def is_deprecated(component: Component) -> bool:
    return component.status == ComponentStatus.DEPRECATED


def can_bind(child: Component, actor_id: uuid.UUID) -> bool:
    """Whether `actor_id` may make `child` the component of a new step. A deprecated version
    keeps working where it already runs, but takes no new dependents; someone else's draft
    is not theirs to see at all."""
    if child.status in LISTED_STATUSES:
        return True
    return is_draft(child) and child.created_by_id == actor_id


def can_transition(component: Component, target: ComponentStatus) -> bool:
    return target in COMPONENT_TRANSITIONS.get(ComponentStatus(component.status), frozenset())


def _transition(component: Component, target: ComponentStatus) -> None:
    if not can_transition(component, target):
        raise IllegalStatusTransitionError(component, target)
    component.status = target


def mark_published(components: Iterable[Component]) -> None:
    for component in components:
        _transition(component, ComponentStatus.PUBLISHED)
        # the first publish only - publishing again after an unpublish keeps it
        if component.first_published_at is None:
            component.first_published_at = datetime.now(UTC)
        # the note belongs to the deprecated status - it never outlives it
        component.deprecation_note = None


def mark_draft(components: Iterable[Component]) -> None:
    """Back to a draft - only ever within the unpublish window, so it counts as never
    published: editable again, and its next publish starts a new window."""
    for component in components:
        _transition(component, ComponentStatus.DRAFT)
        component.deprecation_note = None
        component.first_published_at = None


def mark_deprecated(component: Component, note: str | None) -> None:
    """Retract a public version without breaking what runs it. Deprecating again only
    replaces the note."""
    _transition(component, ComponentStatus.DEPRECATED)
    component.deprecation_note = note


def newer_published(component: Component, versions: Iterable[Component]) -> Component | None:
    """The newest published version of `component`'s lineage above it, if any. While there is
    one, `component` stays out of PUBLISHED - publishing or undeprecating it would put an old
    version back on offer, hidden behind the newer one in every list."""
    newer = [
        v
        for v in versions
        if v.name == component.name and v.version > component.version and v.status in LISTED_STATUSES
    ]
    return max(newer, key=lambda v: v.version, default=None)


def superseded_by(newest: Component, versions: Iterable[Component]) -> list[Component]:
    """The versions of `newest`'s lineage that publishing it supersedes: the older ones still
    published. They are deprecated rather than left listed, so a later unpublish of `newest`
    doesn't silently put an old version back on offer."""
    return [
        v
        for v in versions
        if v.name == newest.name and v.version < newest.version and v.status in LISTED_STATUSES
    ]


def mark_superseded(older: Iterable[Component], newest: Component) -> None:
    for component in older:
        mark_deprecated(component, f"Superseded by v{newest.version}")


def mark_undeprecated(component: Component) -> None:
    if not is_deprecated(component):
        raise IllegalStatusTransitionError(component, ComponentStatus.PUBLISHED)
    mark_published([component])


# --- publishing a tree -----------------------------------------------------------------


def is_settled(workflow: Component) -> bool:
    """Every step needs no further action - always true for a tool, which has none."""
    return all(step.match_status in SETTLED_STEP_STATUSES for step in workflow.steps)


@dataclass(frozen=True)
class PublishCheck:
    """What stands between a component and being published, and what goes public with it."""

    #: the component's own steps are not all settled
    root_unsettled: bool = False
    #: nested workflows with unsettled steps, by name
    unsettled_nested: list[str] = field(default_factory=list)
    #: drafts below it owned by someone else - the actor cannot publish those
    foreign_drafts: list[str] = field(default_factory=list)
    #: the actor's own drafts below it - published along with it, when opted into
    own_drafts: list[Component] = field(default_factory=list)
    #: deprecated versions this publish would give a new public dependent - whoever owns
    #: them. No opt-in resolves it: only replacing the step does
    deprecated_children: list[Component] = field(default_factory=list)


def without_domains(components: Iterable[Component]) -> list[Component]:
    """Those that can't go public: every public component has at least one domain - it is
    how others find and filter it."""
    return [c for c in components if not c.domains]


def can_publish(root: Component, actor_id: uuid.UUID) -> PublishCheck:
    """`root` with its whole tree loaded (see ComponentsRepository.load_tree). A public
    workflow is visible to everyone, so everything below it has to be public too - at any
    depth - and every workflow in the tree has to be settled.

    Deprecated versions below are public, so they don't block on that account. They block
    only where this publish creates a new dependent: as a direct child of `root` or of an
    own draft going public with it. Below an already-public nested workflow the dependency
    is old, and not the actor's to fix.
    """
    below = descendants(root)
    # `== DRAFT`, never "not published": a deprecated child must not be swept up and
    # silently re-published along with its parent
    drafts = [c for c in below if is_draft(c)]
    own_drafts = [c for c in drafts if c.created_by_id == actor_id]
    newly_public = [root, *own_drafts]
    deprecated = {child.id: child for parent in newly_public for child in parent.children if is_deprecated(child)}
    return PublishCheck(
        root_unsettled=not is_settled(root),
        unsettled_nested=sorted({c.name for c in below if c.is_workflow and not is_settled(c)}),
        foreign_drafts=sorted({c.name for c in drafts if c.created_by_id != actor_id}),
        own_drafts=own_drafts,
        deprecated_children=sorted(deprecated.values(), key=lambda c: (c.name, c.version)),
    )


# --- taking a version out of public view -----------------------------------------------


@dataclass(frozen=True)
class RetractImpact:
    """The public workflows above a version that unpublishing or deleting it would break."""

    #: the actor's own published ones - they become drafts along with it, when opted into
    own: list[Component] = field(default_factory=list)
    #: the actor's own deprecated ones - they block: there is no way from DEPRECATED to
    #: DRAFT, so the actor undeprecates them first (or deprecates instead of retracting)
    own_deprecated: list[Component] = field(default_factory=list)
    #: other users' public ones, in any public status - they block, only their owners may
    #: take them down
    foreign: list[Component] = field(default_factory=list)
    #: the actor's own published ones past their unpublish window - they block: they can't
    #: become drafts anymore (deprecating this version instead breaks nothing)
    own_locked: list[Component] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return bool(self.foreign or self.own_deprecated or self.own_locked)


def retract_impact(
    ancestors: Iterable[Component], actor_id: uuid.UUID, now: datetime, window: timedelta
) -> RetractImpact:
    """`ancestors`: every workflow nesting the version, at any depth (see
    ComponentsRepository.find_ancestors). All public ones count, not just the direct parents:
    once a parent becomes a draft, the public workflow nesting that parent runs a draft too."""
    public = sorted((a for a in ancestors if is_public(a)), key=lambda a: (a.name, a.version))
    own = [a for a in public if a.created_by_id == actor_id]
    published = [a for a in own if not is_deprecated(a)]
    return RetractImpact(
        own=[a for a in published if within_unpublish_window(a, now, window)],
        own_deprecated=[a for a in own if is_deprecated(a)],
        foreign=[a for a in public if a.created_by_id != actor_id],
        own_locked=[a for a in published if not within_unpublish_window(a, now, window)],
    )


# --- steps -----------------------------------------------------------------------------


def edited_in_builder(workflow: Component) -> bool:
    """Whether the workflow's builder canvas still exists - then that canvas is the source of
    its steps and generated CWL, and every Save regenerates both from it. Rebinding a step
    anywhere else would diverge from the canvas, wire the CWL to ports the new component may
    not have, and be overwritten by the next Save."""
    return workflow.workflow is not None and workflow.workflow.draft_id is not None


def steps_editable(workflow: Component) -> bool:
    """A public workflow is what others see and nest - its steps only change as a new
    version (or as a draft again, within the unpublish window). A builder workflow's steps
    change in the builder only."""
    return is_draft(workflow) and not edited_in_builder(workflow)


def _step_transition(step: WorkflowStep, target: StepMatchStatus) -> None:
    if target not in STEP_TRANSITIONS[StepMatchStatus(step.match_status)]:
        raise IllegalStepTransitionError(step, target)
    step.match_status = target


def bind_step(step: WorkflowStep, child: Component) -> None:
    """Point the step at `child`. Never confirms it - only confirm_step does - and a
    hand-picked binding has no algorithmic confidence, so the score is cleared."""
    _step_transition(step, StepMatchStatus.SUGGESTED)
    step.component_id = child.id
    # the relationship too, not just the FK - it is what the response serialises
    step.component = child
    step.match_score = None


def unbind_step(step: WorkflowStep) -> None:
    """Clear the step - the user removed its component, or the component is being deleted."""
    _step_transition(step, StepMatchStatus.UNMATCHED)
    step.component_id = None
    step.component = None
    step.match_score = None


def confirm_step(step: WorkflowStep) -> None:
    if step.component_id is None:
        raise IllegalStepTransitionError(step, StepMatchStatus.CONFIRMED)
    _step_transition(step, StepMatchStatus.CONFIRMED)
