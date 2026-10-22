from app.api.dto.workflow_draft import (
    LinkedWorkflowDto,
    SyncedWorkflowDto,
    WorkflowDraftDetailDto,
    WorkflowDraftListItemDto,
)
from app.domain.models.component import Component, ComponentStatus
from app.domain.models.workflow_draft import WorkflowDraft


class WorkflowDraftTransformer:
    @staticmethod
    def to_linked_workflow(workflow: Component | None) -> LinkedWorkflowDto | None:
        if workflow is None:
            return None
        return LinkedWorkflowDto(id=workflow.id, version=workflow.version, status=ComponentStatus(workflow.status))

    @staticmethod
    def to_list_item(draft: WorkflowDraft, linked_workflow: Component | None = None) -> WorkflowDraftListItemDto:
        return WorkflowDraftListItemDto(
            id=draft.id,
            name=draft.name,
            node_count=draft.node_count,
            updated_at=draft.updated_at,
            linked_workflow=WorkflowDraftTransformer.to_linked_workflow(linked_workflow),
        )

    @staticmethod
    def to_detail(
        draft: WorkflowDraft,
        linked_workflow: Component | None = None,
        missing_component_ids: list[str] | None = None,
    ) -> WorkflowDraftDetailDto:
        return WorkflowDraftDetailDto(
            id=draft.id,
            name=draft.name,
            canvas_state=draft.canvas_state,
            node_count=draft.node_count,
            updated_at=draft.updated_at,
            created_at=draft.created_at,
            linked_workflow=WorkflowDraftTransformer.to_linked_workflow(linked_workflow),
            missing_component_ids=missing_component_ids or [],
        )

    @staticmethod
    def to_synced(workflow: Component) -> SyncedWorkflowDto:
        return SyncedWorkflowDto(
            workflow_id=workflow.id,
            name=workflow.name,
            step_count=len(workflow.steps),
            version=workflow.version,
            status=ComponentStatus(workflow.status),
        )
