import uuid
from dataclasses import dataclass

from sqlalchemy import or_
from sqlalchemy.orm import aliased, selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.component import Component, ComponentStatus
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import WorkflowStep
from app.infrastructure.db.session import require_unit_of_work


@dataclass(frozen=True)
class ComponentUsageRow:
    """One workflow version using a component lineage - one row per child version it uses."""

    workflow_id: uuid.UUID
    workflow_name: str
    workflow_version: int
    workflow_status: ComponentStatus
    component_version: int


class WorkflowsRepository:
    """What only the composite side has: steps (the edges to child components), the
    builder-draft link, and the reverse lookup from a child to the workflows using it.
    Workflows themselves are Components - listing and loading them is ComponentsRepository's."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_usages_of_lineage(self, name: str, visible_to: uuid.UUID | None) -> list[ComponentUsageRow]:
        """Every workflow version with a step bound to any version of the lineage `name` -
        a tool, or a nested workflow - restricted to what `visible_to` may see (published
        workflows, plus their own drafts). Selects columns only - loading whole workflows
        would pull in all their steps and domains just to print a name."""
        parent = aliased(Component)
        child = aliased(Component)
        visible = parent.status == ComponentStatus.PUBLISHED
        if visible_to is not None:
            visible = or_(visible, parent.created_by_id == visible_to)
        query = (
            select(parent.id, parent.name, parent.version, parent.status, child.version)
            .join(WorkflowStep, WorkflowStep.workflow_id == parent.id)
            .join(child, child.id == WorkflowStep.component_id)
            .where(child.name == name, visible)
            .distinct()
            .order_by(parent.name, parent.version, child.version)
        )
        rows = (await self.db.exec(query)).all()
        return [
            ComponentUsageRow(
                workflow_id=workflow_id,
                workflow_name=workflow_name,
                workflow_version=workflow_version,
                workflow_status=ComponentStatus(status),
                component_version=component_version,
            )
            for workflow_id, workflow_name, workflow_version, status, component_version in rows
        ]

    async def find_latest_by_draft_id(self, draft_id: uuid.UUID) -> Component | None:
        """The newest workflow version synced from this builder draft - every version synced
        from one draft carries its id."""
        query = (
            select(Component)
            .join(Workflow, Workflow.component_id == Component.id)
            .where(Workflow.draft_id == draft_id)
            .order_by(Component.version.desc())
        )
        result = await self.db.exec(query)
        return result.first()

    async def find_all_synced_from_draft(self, draft_id: uuid.UUID) -> list[Component]:
        """Every workflow version synced from this builder draft."""
        query = (
            select(Component)
            .join(Workflow, Workflow.component_id == Component.id)
            .where(Workflow.draft_id == draft_id)
            .order_by(Component.version)
        )
        result = await self.db.exec(query)
        return list(result.all())

    async def find_all_by_draft_ids(self, draft_ids: set[uuid.UUID]) -> list[Component]:
        """The newest workflow version per draft, for every draft in the set."""
        if not draft_ids:
            return []
        query = (
            select(Component)
            .join(Workflow, Workflow.component_id == Component.id)
            .where(Workflow.draft_id.in_(draft_ids))
            .distinct(Workflow.draft_id)
            .order_by(Workflow.draft_id, Component.version.desc())
        )
        result = await self.db.exec(query)
        return list(result.all())

    async def find_step_by_id(self, step_id: uuid.UUID) -> WorkflowStep | None:
        return await self.db.get(WorkflowStep, step_id)

    async def find_steps_by_component_id(self, component_id: uuid.UUID) -> list[WorkflowStep]:
        """Every step pinned to exactly this component version (not its whole lineage -
        that is find_usages_of_lineage), with its parent workflow loaded."""
        query = (
            select(WorkflowStep)
            .where(WorkflowStep.component_id == component_id)
            .options(selectinload(WorkflowStep.workflow).selectinload(Workflow.component))
        )
        result = await self.db.exec(query)
        return list(result.all())

    async def add_steps(self, steps: list[WorkflowStep], workflows: list[Component]) -> None:
        """Step edits together with the workflows they touch."""
        require_unit_of_work(self.db)
        self.db.add_all([*steps, *workflows])
        await self.db.flush()

    async def add_step(self, step: WorkflowStep) -> WorkflowStep:
        require_unit_of_work(self.db)
        self.db.add(step)
        await self.db.flush()
        return step
