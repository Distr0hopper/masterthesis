"""A step's configuration is exactly one decision - the DTO refuses anything ambiguous
before the service ever sees it."""

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.api.dto.workflow import ComponentConfigDto
from app.api.transformer.workflow_draft_transformer import WorkflowDraftTransformer
from app.domain.models.component import Component, ComponentKind, ComponentStatus
from app.domain.models.workflow_draft import WorkflowDraft


def test_a_new_version_needs_nothing_but_its_target() -> None:
    # name and domains are the target lineage's
    config = ComponentConfigDto(step_id="a", new_version_of_id=uuid.uuid4())
    assert config.name is None and config.domains is None


@pytest.mark.parametrize(
    "fields",
    [
        {"reuse_component_id": uuid.uuid4(), "new_version_of_id": uuid.uuid4()},
        {"new_version_of_id": uuid.uuid4(), "name": "renamed"},
        {"new_version_of_id": uuid.uuid4(), "domains": ["other"]},
    ],
    ids=["reuse-and-new-version", "new-version-with-name", "new-version-with-domains"],
)
def test_a_new_version_is_not_combined_with_another_branch(fields: dict) -> None:
    with pytest.raises(ValidationError):
        ComponentConfigDto(step_id="a", **fields)


def test_without_reuse_or_new_version_a_step_needs_a_name() -> None:
    with pytest.raises(ValidationError, match="newVersionOfId"):
        ComponentConfigDto(step_id="a", domains=["other"])


def test_a_draft_names_the_version_its_next_save_works_on() -> None:
    now = datetime.now(UTC)
    draft = WorkflowDraft(
        id=uuid.uuid4(), name="pipeline", canvas_state="{}", node_count=0, created_by_id=uuid.uuid4(), updated_at=now
    )
    # loaded rows carry their status as a plain str
    v2 = Component(id=uuid.uuid4(), kind=ComponentKind.WORKFLOW, name="pipeline", version=2, cwl_content="", status="published")

    linked = WorkflowDraftTransformer.to_list_item(draft, v2).linked_workflow
    assert linked is not None and (linked.id, linked.version, linked.status) == (v2.id, 2, ComponentStatus.PUBLISHED)
    assert WorkflowDraftTransformer.to_list_item(draft).linked_workflow is None
