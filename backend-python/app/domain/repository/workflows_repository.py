import uuid
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends
from sqlalchemy import String, and_, cast, or_
from sqlalchemy.orm import selectinload
from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.component import Component
from app.domain.models.component_domain import DOMAIN_AGNOSTIC
from app.domain.models.favorite import Favorite, FavoriteEntityType
from app.domain.models.workflow import Workflow, WorkflowStatus
from app.domain.models.workflow_domain import WorkflowDomain
from app.domain.models.workflow_step import WorkflowStep
from app.domain.pagination.pagination import PaginatedList
from app.infrastructure.db.session import get_db


@dataclass
class WorkflowListFilter:
    domains: list[str] = field(default_factory=list)
    search: str | None = None
    status: WorkflowStatus | None = None
    created_by: uuid.UUID | None = None
    exclude_created_by: uuid.UUID | None = None
    favorited_by: uuid.UUID | None = None


@dataclass(frozen=True)
class WorkflowComponentUsage:
    """One workflow using a component lineage - one row per version it uses."""

    workflow_id: uuid.UUID
    workflow_name: str
    workflow_status: WorkflowStatus
    component_version: int


class WorkflowsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_usages_of_component(
        self, component_name: str, visible_to: uuid.UUID | None
    ) -> list[WorkflowComponentUsage]:
        """Every workflow with a step bound to any version of the component lineage
        `component_name`, restricted to what `visible_to` may see (validated workflows,
        plus their own pending ones). Selects columns only - loading whole workflows would
        pull in all their steps and domains just to print a name."""
        visible = Workflow.status == WorkflowStatus.VALIDATED
        if visible_to is not None:
            visible = or_(visible, Workflow.created_by_id == visible_to)
        query = (
            select(Workflow.id, Workflow.name, Workflow.status, Component.version)
            .join(WorkflowStep, WorkflowStep.workflow_id == Workflow.id)
            .join(Component, Component.id == WorkflowStep.component_id)
            .where(Component.name == component_name, visible)
            .distinct()
            .order_by(Workflow.name, Component.version)
        )
        rows = (await self.db.exec(query)).all()
        return [
            WorkflowComponentUsage(
                workflow_id=workflow_id,
                workflow_name=name,
                workflow_status=WorkflowStatus(status),
                component_version=version,
            )
            for workflow_id, name, status, version in rows
        ]

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "WorkflowsRepository":
        return WorkflowsRepository(db)

    def _apply_filters(self, query, filter: WorkflowListFilter):
        if filter.status is not None:
            query = query.where(Workflow.status == filter.status)
        if filter.created_by is not None:
            query = query.where(Workflow.created_by_id == filter.created_by)
        if filter.exclude_created_by is not None:
            query = query.where(
                or_(Workflow.created_by_id != filter.exclude_created_by, Workflow.created_by_id.is_(None))
            )
        if filter.favorited_by is not None:
            query = query.join(
                Favorite,
                and_(
                    Favorite.entity_type == FavoriteEntityType.WORKFLOW,
                    Favorite.entity_ref == cast(Workflow.id, String),
                    Favorite.user_id == filter.favorited_by,
                ),
            )
        if filter.domains:
            matching = {*filter.domains, DOMAIN_AGNOSTIC}
            query = query.where(
                Workflow.id.in_(
                    select(WorkflowDomain.workflow_id).where(WorkflowDomain.domain.in_(matching))
                )
            )
        if filter.search is not None:
            query = query.where(Workflow.name.ilike(f"%{filter.search}%"))
        return query

    async def find_all(self) -> list[Workflow]:
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

    async def find_by_id_with_steps(self, workflow_id: uuid.UUID) -> Workflow | None:
        """Same as find_by_id, but forces a fresh SELECT with explicit nested eager
        loading of steps.component - unlike db.get(), which returns straight from the
        identity map (skipping any query at all) when the workflow is already resident,
        this guarantees steps.component is populated even right after a request that ran
        several intermediate commits (e.g. creating new Components mid-request), where
        those earlier commits leave every attribute expired and a bare identity-map hit
        would leave step.component unpopulated - accessing it later would then attempt a
        genuine lazy load outside of any async-safe context and crash with MissingGreenlet.
        """
        query = (
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.steps).selectinload(WorkflowStep.component))
        )
        result = await self.db.exec(query)
        return result.first()

    async def find_latest_by_name(self, name: str, exclude_id: uuid.UUID | None = None) -> Workflow | None:
        """The most recently created workflow with this exact name, if any.

        Workflow names are NOT unique (no constraint, no version lineage - unlike
        Component). This backs an advisory "that name is already in use" notice, not a
        rule, so it deliberately returns just the newest match rather than all of them.

        `exclude_id` skips one workflow - a saved workflow trivially matches its own name,
        so the publish-time check has to leave itself out or it would always warn.
        """
        query = select(Workflow).where(Workflow.name == name)
        if exclude_id is not None:
            query = query.where(Workflow.id != exclude_id)
        query = query.order_by(Workflow.created_at.desc())
        result = await self.db.exec(query)
        return result.first()

    async def find_by_draft_id(self, draft_id: uuid.UUID) -> Workflow | None:
        query = select(Workflow).where(Workflow.draft_id == draft_id)
        result = await self.db.exec(query)
        return result.first()

    async def find_all_by_draft_ids(self, draft_ids: set[uuid.UUID]) -> list[Workflow]:
        """Every Workflow whose draft_id is in the set - at most one per draft."""
        if not draft_ids:
            return []
        query = select(Workflow).where(Workflow.draft_id.in_(draft_ids))
        result = await self.db.exec(query)
        return list(result.all())

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

    async def find_step_by_id_with_relations(self, step_id: uuid.UUID) -> WorkflowStep | None:
        """Fresh SELECT of a step with its component and workflow eagerly loaded - the
        find_by_id_with_steps counterpart for a single step. populate_existing because the
        step is usually already resident with attributes a later commit/refresh unloaded."""
        query = (
            select(WorkflowStep)
            .where(WorkflowStep.id == step_id)
            .options(selectinload(WorkflowStep.component), selectinload(WorkflowStep.workflow))
            .execution_options(populate_existing=True)
        )
        result = await self.db.exec(query)
        return result.first()

    async def find_steps_by_component_id(self, component_id: uuid.UUID) -> list[WorkflowStep]:
        """Every step pinned to exactly this component version (not its whole lineage -
        that is find_usages_of_component), with its workflow loaded."""
        query = (
            select(WorkflowStep)
            .where(WorkflowStep.component_id == component_id)
            .options(selectinload(WorkflowStep.workflow))
        )
        result = await self.db.exec(query)
        return list(result.all())

    async def save_steps(self, steps: list[WorkflowStep], workflows: list[Workflow]) -> None:
        """Persist several step and workflow edits in one commit, so a cascade never
        leaves half of them applied."""
        self.db.add_all([*steps, *workflows])
        await self.db.commit()

    async def save_step(self, step: WorkflowStep) -> WorkflowStep:
        self.db.add(step)
        await self.db.commit()
        await self.db.refresh(step)
        return step
