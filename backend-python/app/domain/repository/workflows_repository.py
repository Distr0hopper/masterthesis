import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.workflow import Workflow, WorkflowStatus
from app.domain.models.workflow_domain import WorkflowDomain
from app.domain.models.workflow_step import WorkflowStep
from app.domain.pagination.pagination import PaginatedList
from app.infrastructure.db.session import get_db


@dataclass
class WorkflowListFilter:
    domain: str | None = None
    search: str | None = None
    status: WorkflowStatus | None = None
    created_by: uuid.UUID | None = None


class WorkflowsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "WorkflowsRepository":
        return WorkflowsRepository(db)

    def _apply_filters(self, query, filter: WorkflowListFilter):
        if filter.status is not None:
            query = query.where(Workflow.status == filter.status)
        if filter.created_by is not None:
            query = query.where(Workflow.created_by_id == filter.created_by)
        if filter.domain is not None:
            # (workflow_id, domain) is WorkflowDomain's composite PK, so this join
            # matches at most one row per workflow for a single domain value - no fan-out
            query = query.join(WorkflowDomain, WorkflowDomain.workflow_id == Workflow.id).where(
                WorkflowDomain.domain == filter.domain
            )
        if filter.search is not None:
            query = query.where(Workflow.name.ilike(f"%{filter.search}%"))
        return query

    async def find_all(self) -> list[Workflow]:
        # VALIDATED-only, matching the public browse list's visibility rule - only backs
        # get_latest_workflows now; the paginated browse/mine endpoints go through
        # find_paginated instead
        query = select(Workflow).where(Workflow.status == WorkflowStatus.VALIDATED).order_by(Workflow.created_at.desc())
        result = await self.db.exec(query)
        return list(result.all())

    async def find_paginated(self, filter: WorkflowListFilter, pagination: PaginatedList) -> tuple[list[Workflow], int]:
        base_query = self._apply_filters(select(Workflow), filter)

        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.exec(count_query)).one()

        items_query = base_query.order_by(Workflow.created_at.desc()).limit(pagination.limit).offset(pagination.offset)
        result = await self.db.exec(items_query)
        return list(result.all()), total

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
