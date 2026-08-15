import uuid
from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.workflow import Workflow, WorkflowStatus
from app.domain.models.workflow_domain import WorkflowDomain
from app.domain.models.workflow_step import WorkflowStep
from app.infrastructure.db.session import get_db


class WorkflowsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "WorkflowsRepository":
        return WorkflowsRepository(db)

    async def find_all(self, domain: str | None = None) -> list[Workflow]:
        # this backs only the public browse list - pending workflows are never visible
        # here regardless of who's asking (see WorkflowsService.get_visible_workflow for
        # the creator-only detail/download bypass, and find_by_created_by below for "mine")
        query = select(Workflow).where(Workflow.status == WorkflowStatus.VALIDATED).order_by(Workflow.created_at.desc())
        if domain is not None:
            query = query.join(WorkflowDomain, WorkflowDomain.workflow_id == Workflow.id).where(
                WorkflowDomain.domain == domain
            )
        result = await self.db.exec(query)
        return list(result.all())

    async def find_by_created_by(self, created_by_id: uuid.UUID) -> list[Workflow]:
        query = (
            select(Workflow).where(Workflow.created_by_id == created_by_id).order_by(Workflow.created_at.desc())
        )
        result = await self.db.exec(query)
        return list(result.all())

    async def find_by_id(self, workflow_id: uuid.UUID) -> Workflow | None:
        return await self.db.get(Workflow, workflow_id)

    async def save(self, workflow: Workflow) -> Workflow:
        self.db.add(workflow)
        await self.db.commit()
        await self.db.refresh(workflow)
        return workflow

    async def delete(self, workflow: Workflow) -> None:
        await self.db.delete(workflow)
        await self.db.commit()

    async def find_step_by_id(self, step_id: uuid.UUID) -> WorkflowStep | None:
        return await self.db.get(WorkflowStep, step_id)

    async def save_step(self, step: WorkflowStep) -> WorkflowStep:
        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        return step
