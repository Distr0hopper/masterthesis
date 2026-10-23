"""Rows for the database tests - users, tools and workflows saved straight through a
session, bypassing the use cases, so a test sets up exactly the state it is about."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.component import Component, ComponentKind, ComponentSource, ComponentStatus
from app.domain.models.component_domain import ComponentDomain
from app.domain.models.tool import Tool
from app.domain.models.user import User
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import StepMatchStatus, WorkflowStep
from app.infrastructure.security.security import create_access_token

SessionFactory = Callable[[], AsyncSession]

TOOL_CWL = "cwlVersion: v1.2\nclass: CommandLineTool\nbaseCommand: [echo]\ninputs: {}\noutputs: {}\n"
WORKFLOW_CWL = "cwlVersion: v1.2\nclass: Workflow\ninputs: {}\noutputs: {}\nsteps: {}\n"


def user(email: str | None = None) -> User:
    return User(email=email or f"{uuid.uuid4().hex[:8]}@example.com")


def bearer(owner: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(owner.id), owner.email)}"}


def _component(
    kind: ComponentKind,
    name: str,
    owner: User | None,
    status: ComponentStatus,
    version: int,
    domains: tuple[str, ...],
    cwl: str,
) -> Component:
    component = Component(
        kind=kind,
        name=name,
        version=version,
        created_by_id=owner.id if owner is not None else None,
        cwl_content=cwl,
        source=ComponentSource.MANUAL_UPLOAD,
        status=status,
        first_published_at=datetime.now(UTC) if status != ComponentStatus.DRAFT else None,
    )
    component.domains = [ComponentDomain(component_id=component.id, domain=d) for d in domains]
    return component


def tool(
    name: str,
    owner: User | None,
    status: ComponentStatus = ComponentStatus.PUBLISHED,
    version: int = 1,
    domains: tuple[str, ...] = ("animal_behavior",),
) -> Component:
    component = _component(ComponentKind.TOOL, name, owner, status, version, domains, TOOL_CWL)
    component.tool = Tool(component_id=component.id)
    return component


def workflow(
    name: str,
    owner: User | None,
    *children: Component,
    status: ComponentStatus = ComponentStatus.PUBLISHED,
    version: int = 1,
) -> Component:
    component = _component(ComponentKind.WORKFLOW, name, owner, status, version, ("animal_behavior",), WORKFLOW_CWL)
    component.workflow = Workflow(
        component_id=component.id,
        steps=[
            WorkflowStep(
                workflow_id=component.id,
                step_id=f"step_{child.name}",
                run_reference=f"{child.name}.cwl",
                step_order=i,
                component_id=child.id,
                match_status=StepMatchStatus.CONFIRMED,
            )
            for i, child in enumerate(children)
        ],
    )
    return component


async def save(sessions: SessionFactory, *rows: object) -> None:
    """Saves the rows in their own session, committed (to the test's savepoint) - the way a
    request sees what an earlier one wrote."""
    async with sessions() as session:
        session.add_all(rows)
        await session.commit()
