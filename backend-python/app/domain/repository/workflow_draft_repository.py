import uuid
from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.workflow_draft import WorkflowDraft
from app.infrastructure.db.session import get_db


class WorkflowDraftRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "WorkflowDraftRepository":
        return WorkflowDraftRepository(db)

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

    async def find_by_id(self, draft_id: uuid.UUID) -> WorkflowDraft | None:
        return await self.db.get(WorkflowDraft, draft_id)

    async def save(self, draft: WorkflowDraft) -> WorkflowDraft:
        self.db.add(draft)
        await self.db.commit()
        await self.db.refresh(draft)
        return draft

    async def delete(self, draft: WorkflowDraft) -> None:
        await self.db.delete(draft)
        await self.db.commit()
