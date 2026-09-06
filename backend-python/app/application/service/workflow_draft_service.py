import uuid
from typing import Annotated

from fastapi import Depends

from app.application.exception.workflow_draft_exceptions import (
    WorkflowDraftForbiddenError,
    WorkflowDraftNotFoundError,
)
from app.domain.models.workflow_draft import WorkflowDraft
from app.domain.repository.workflow_draft_repository import WorkflowDraftRepository


class WorkflowDraftService:
    def __init__(self, repository: WorkflowDraftRepository):
        self.repository = repository

    @staticmethod
    def get_service(
        repository: Annotated[WorkflowDraftRepository, Depends(WorkflowDraftRepository.get_repository)],
    ) -> "WorkflowDraftService":
        return WorkflowDraftService(repository)

    async def list_my_drafts(self, user_id: uuid.UUID) -> list[WorkflowDraft]:
        return await self.repository.find_all_by_user(user_id)

    async def get_draft(self, draft_id: uuid.UUID, user_id: uuid.UUID) -> WorkflowDraft:
        """Fetch one draft, enforcing ownership. Every mutating path goes through this."""
        draft = await self.repository.find_by_id(draft_id)
        if draft is None:
            raise WorkflowDraftNotFoundError(draft_id)
        if draft.created_by_id != user_id:
            raise WorkflowDraftForbiddenError()
        return draft

    async def create_draft(
        self,
        name: str,
        canvas_state: str,
        node_count: int,
        user_id: uuid.UUID,
    ) -> WorkflowDraft:
        draft = WorkflowDraft(
            name=name,
            canvas_state=canvas_state,
            node_count=node_count,
            created_by_id=user_id,
        )
        return await self.repository.save(draft)

    async def update_draft(
        self,
        draft: WorkflowDraft,
        name: str,
        canvas_state: str,
        node_count: int,
    ) -> WorkflowDraft:
        # full replacement, not a patch - the editor always sends its complete canvas
        draft.name = name
        draft.canvas_state = canvas_state
        draft.node_count = node_count
        return await self.repository.save(draft)

    async def delete_draft(self, draft: WorkflowDraft) -> None:
        await self.repository.delete(draft)
