"""Deleting a component version cascades into the workflows and drafts that use it."""

import asyncio
import json
import uuid

from app.application.exception.workflow_draft_exceptions import ExportValidationError
from app.application.service.workflow_draft_service import WorkflowDraftService
from app.application.service.workflows_service import WorkflowsService
from app.domain.models.component import Component
from app.domain.models.user import User
from app.domain.models.workflow import Workflow, WorkflowStatus
from app.domain.models.workflow_draft import WorkflowDraft
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep

OWNER = uuid.uuid4()
STRANGER = uuid.uuid4()


class FakeWorkflowsRepository:
    def __init__(self, steps: list[WorkflowStep]):
        self.steps = steps
        self.saved: tuple[list[WorkflowStep], list[Workflow]] | None = None

    async def find_steps_by_component_id(self, component_id: uuid.UUID) -> list[WorkflowStep]:
        return [s for s in self.steps if s.component_id == component_id]

    async def save_steps(self, steps: list[WorkflowStep], workflows: list[Workflow]) -> None:
        self.saved = (steps, workflows)


class FakeDraftRepository:
    def __init__(self, drafts: list[WorkflowDraft]):
        self.drafts = drafts

    async def find_all_mentioning(self, needle: str) -> list[WorkflowDraft]:
        return [d for d in self.drafts if needle in d.canvas_state]


class FakeComponentsRepository:
    def __init__(self, components: list[Component]):
        self.by_id = {c.id: c for c in components}

    async def find_by_id(self, component_id: uuid.UUID) -> Component | None:
        return self.by_id.get(component_id)


def component() -> Component:
    return Component(id=uuid.uuid4(), name="thin-data", version=2, cwl_content="", created_by_id=OWNER)


def workflow(name: str, status: WorkflowStatus, created_by: uuid.UUID = OWNER) -> Workflow:
    return Workflow(id=uuid.uuid4(), name=name, cwl_content="", status=status, created_by_id=created_by)


def step(wf: Workflow, component_id: uuid.UUID | None, status: StepMatchStatus) -> WorkflowStep:
    s = WorkflowStep(
        id=uuid.uuid4(),
        workflow_id=wf.id,
        step_id="step",
        run_reference="x.cwl",
        step_order=0,
        component_id=component_id,
        match_status=status,
        match_score=0.9,
    )
    s.workflow = wf
    return s


def draft(owner: uuid.UUID, *component_ids: uuid.UUID, name: str = "draft") -> WorkflowDraft:
    nodes = [{"id": f"n{i}", "data": {"componentId": str(cid)}} for i, cid in enumerate(component_ids)]
    return WorkflowDraft(id=uuid.uuid4(), name=name, canvas_state=json.dumps({"nodes": nodes}), created_by_id=owner)


def service(steps: list[WorkflowStep], drafts: list[WorkflowDraft] | None = None) -> WorkflowsService:
    return WorkflowsService(
        FakeWorkflowsRepository(steps),  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        None,  # type: ignore[arg-type]
        FakeDraftRepository(drafts or []),  # type: ignore[arg-type]
    )


def test_detach_unmatches_steps_and_unpublishes_their_workflows() -> None:
    target = component()
    published = workflow("public", WorkflowStatus.VALIDATED)
    pending = workflow("pending", WorkflowStatus.PENDING_VALIDATION)
    confirmed = step(published, target.id, StepMatchStatus.CONFIRMED)
    suggested = step(pending, target.id, StepMatchStatus.SUGGESTED)
    unrelated = step(published, uuid.uuid4(), StepMatchStatus.CONFIRMED)
    svc = service([confirmed, suggested, unrelated])

    asyncio.run(svc.detach_component(target.id))

    for s in (confirmed, suggested):
        assert (s.component_id, s.match_status, s.match_score) == (None, StepMatchStatus.UNMATCHED, None)
    assert unrelated.match_status == StepMatchStatus.CONFIRMED
    assert published.status == WorkflowStatus.PENDING_VALIDATION
    assert pending.status == WorkflowStatus.PENDING_VALIDATION
    saved_steps, saved_workflows = svc.workflows_repository.saved  # type: ignore[attr-defined]
    assert saved_steps == [confirmed, suggested]
    assert saved_workflows == [published]


def test_detach_without_usages_writes_nothing() -> None:
    svc = service([])
    asyncio.run(svc.detach_component(uuid.uuid4()))
    assert svc.workflows_repository.saved is None  # type: ignore[attr-defined]


def test_deletion_impact_names_only_what_the_deleter_may_see() -> None:
    target = component()
    public = workflow("b-public", WorkflowStatus.VALIDATED, created_by=STRANGER)
    mine = workflow("a-mine", WorkflowStatus.PENDING_VALIDATION)
    private = workflow("private", WorkflowStatus.PENDING_VALIDATION, created_by=STRANGER)
    steps = [
        step(public, target.id, StepMatchStatus.CONFIRMED),
        step(public, target.id, StepMatchStatus.CONFIRMED),  # same workflow twice
        step(mine, target.id, StepMatchStatus.SUGGESTED),
        step(private, target.id, StepMatchStatus.SUGGESTED),
    ]
    other = uuid.uuid4()
    drafts = [
        draft(OWNER, target.id, name="z-mine"),
        draft(OWNER, other, target.id, name="y-mine"),
        draft(STRANGER, target.id),
        draft(OWNER, other),
    ]
    # text-only mention, e.g. in a label - must not count as a usage
    drafts.append(
        WorkflowDraft(
            id=uuid.uuid4(),
            name="mention",
            canvas_state=json.dumps({"nodes": [{"id": "a", "data": {"label": str(target.id)}}]}),
            created_by_id=OWNER,
        )
    )
    user = User(id=OWNER, email="o@x")

    impact = asyncio.run(service(steps, drafts).get_deletion_impact(target, user))

    assert [u.workflow_name for u in impact.workflows] == ["a-mine", "b-public"]
    assert impact.workflows[0].component_versions == [2]
    assert impact.hidden_workflow_count == 1
    assert [d.name for d in impact.own_drafts] == ["y-mine", "z-mine"]
    assert impact.other_draft_count == 1


def draft_service(components: list[Component]) -> WorkflowDraftService:
    return WorkflowDraftService(None, FakeComponentsRepository(components), None)  # type: ignore[arg-type]


def test_missing_component_ids_lists_only_deleted_components() -> None:
    kept = component()
    gone = uuid.uuid4()
    svc = draft_service([kept])

    missing = asyncio.run(svc.missing_component_ids(draft(OWNER, kept.id, gone, gone)))

    assert missing == [str(gone)]


def test_missing_component_ids_of_an_unreadable_canvas_is_empty() -> None:
    bad = WorkflowDraft(id=uuid.uuid4(), name="bad", canvas_state="{", created_by_id=OWNER)
    assert asyncio.run(draft_service([]).missing_component_ids(bad)) == []


def test_export_of_a_malformed_canvas_is_a_validation_error_not_a_crash() -> None:
    bad = WorkflowDraft(
        id=uuid.uuid4(), name="bad", canvas_state='{"nodes": [{"id": "a", "data": null}]}', created_by_id=OWNER
    )
    try:
        asyncio.run(draft_service([]).export_to_zip(bad))
    except ExportValidationError as err:
        assert "no linked component" in str(err)
    else:
        raise AssertionError("expected ExportValidationError")
