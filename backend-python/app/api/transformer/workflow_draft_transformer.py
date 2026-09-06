from app.api.dto.workflow_draft import WorkflowDraftDetailDto, WorkflowDraftListItemDto
from app.domain.models.workflow_draft import WorkflowDraft


class WorkflowDraftTransformer:
    @staticmethod
    def to_list_item(draft: WorkflowDraft) -> WorkflowDraftListItemDto:
        return WorkflowDraftListItemDto(
            id=draft.id,
            name=draft.name,
            node_count=draft.node_count,
            updated_at=draft.updated_at,
        )

    @staticmethod
    def to_detail(draft: WorkflowDraft) -> WorkflowDraftDetailDto:
        return WorkflowDraftDetailDto(
            id=draft.id,
            name=draft.name,
            canvas_state=draft.canvas_state,
            node_count=draft.node_count,
            updated_at=draft.updated_at,
            created_at=draft.created_at,
        )
