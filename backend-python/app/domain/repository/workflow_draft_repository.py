import uuid

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.workflow_draft import WorkflowDraft
from app.infrastructure.db.session import require_unit_of_work


class WorkflowDraftRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_all_by_user(self, user_id: uuid.UUID) -> list[WorkflowDraft]:
        # most-recently-saved first: the overview's ordering, so re-saving a draft moves
        # it back to the top without the frontend having to sort
        query = (
            select(WorkflowDraft)
            .where(WorkflowDraft.created_by_id == user_id)
            .order_by(WorkflowDraft.updated_at.desc())
        )
        result = await self.db.exec(query)
        return list(result.all())

    async def find_all_mentioning(self, needle: str) -> list[WorkflowDraft]:
        """Drafts whose raw canvas text contains `needle` - a cheap pre-filter only, since
        canvas_state is opaque text; callers parse the canvas to confirm a real match."""
        query = select(WorkflowDraft).where(col(WorkflowDraft.canvas_state).contains(needle))
        result = await self.db.exec(query)
        return list(result.all())

    async def find_by_id(self, draft_id: uuid.UUID) -> WorkflowDraft | None:
        return await self.db.get(WorkflowDraft, draft_id)

    async def add(self, draft: WorkflowDraft) -> WorkflowDraft:
        require_unit_of_work(self.db)
        self.db.add(draft)
        await self.db.flush()
        return draft

    async def delete(self, draft: WorkflowDraft) -> None:
        require_unit_of_work(self.db)
        await self.db.delete(draft)
        await self.db.flush()
