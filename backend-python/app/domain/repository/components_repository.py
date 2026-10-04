import uuid
from dataclasses import dataclass, field

from sqlalchemy import case, exists, update
from sqlalchemy.orm import aliased, selectinload
from sqlmodel import and_, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.component import Component, ComponentKind, ComponentStatus
from app.domain.models.component_domain import DOMAIN_AGNOSTIC, ComponentDomain
from app.domain.models.favorite import Favorite
from app.domain.models.tool import Tool
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import WorkflowStep
from app.domain.pagination.pagination import PaginatedList
from app.infrastructure.db.session import require_unit_of_work


@dataclass
class ComponentListFilter:
    #: None lists both kinds - the composite's uniform view
    kind: ComponentKind | None = None
    domains: list[str] = field(default_factory=list)
    created_by: uuid.UUID | None = None
    exclude_created_by: uuid.UUID | None = None
    favorited_by: uuid.UUID | None = None
    search: str | None = None
    #: None for any status - e.g. lifecycle.LISTED_STATUSES for the public lists
    statuses: frozenset[ComponentStatus] | None = None
    favorites_first_for: uuid.UUID | None = None


#: one level of the composite, eagerly: a workflow's steps, each step's child, and the
#: child's own kind-specific row - everything Component.children touches, so walking one
#: level never falls back to a lazy load (which an AsyncSession cannot do)
_ONE_LEVEL = (
    selectinload(Component.tool),
    selectinload(Component.workflow)
    .selectinload(Workflow.steps)
    .selectinload(WorkflowStep.component)
    .options(selectinload(Component.tool), selectinload(Component.workflow)),
)


class ComponentsRepository:
    """Both kinds of the composite, queried uniformly through their shared base row."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _apply_filters(self, query, filter: ComponentListFilter):
        if filter.kind is not None:
            query = query.where(Component.kind == filter.kind)
        if filter.domains:
            matching = {*filter.domains, DOMAIN_AGNOSTIC}
            query = query.where(
                Component.id.in_(
                    select(ComponentDomain.component_id).where(ComponentDomain.domain.in_(matching))
                )
            )
        if filter.statuses is not None:
            query = query.where(Component.status.in_(filter.statuses))
        if filter.created_by is not None:
            query = query.where(Component.created_by_id == filter.created_by)
        if filter.exclude_created_by is not None:
            query = query.where(
                or_(Component.created_by_id != filter.exclude_created_by, Component.created_by_id.is_(None))
            )
        if filter.favorited_by is not None:
            query = query.join(
                Favorite,
                and_(Favorite.component_name == Component.name, Favorite.user_id == filter.favorited_by),
            )
        if filter.search is not None:
            query = query.where(Component.name.ilike(f"%{filter.search}%"))
        return query

    async def find_all(
        self, statuses: frozenset[ComponentStatus] | None = None, kind: ComponentKind | None = None
    ) -> list[Component]:
        """The latest version of every lineage."""
        query = self._apply_filters(select(Component).distinct(Component.name), ComponentListFilter(statuses=statuses, kind=kind))
        query = query.order_by(Component.name, Component.version.desc())
        result = await self.db.exec(query)
        return list(result.all())

    async def find_paginated(
        self, filter: ComponentListFilter, pagination: PaginatedList
    ) -> tuple[list[Component], int]:
        base_query = self._apply_filters(select(Component).distinct(Component.name), filter)

        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.exec(count_query)).one()

        # DISTINCT ON (name) keeps the first row per name, so it must be ordered by name and
        # then newest version first - that's what makes each row the latest version
        latest_per_name = base_query.order_by(Component.name, Component.version.desc())
        if filter.favorites_first_for is None:
            items_query = latest_per_name
        else:
            # a different order needs an outer query: Postgres requires DISTINCT ON's
            # expressions to lead the ORDER BY of the same query
            latest = aliased(Component, latest_per_name.subquery())
            is_favorite = exists().where(
                Favorite.component_name == latest.name,
                Favorite.user_id == filter.favorites_first_for,
            )
            items_query = select(latest).order_by(case((is_favorite, 0), else_=1), latest.name)

        result = await self.db.exec(items_query.limit(pagination.limit).offset(pagination.offset))
        return list(result.all()), total

    async def find_all_filtered(self, filter: ComponentListFilter) -> list[Component]:
        """find_paginated without the paging - the latest version per name, by name."""
        query = self._apply_filters(select(Component).distinct(Component.name), filter).order_by(
            Component.name, Component.version.desc()
        )
        result = await self.db.exec(query)
        return list(result.all())

    async def find_by_ids(self, ids: list[uuid.UUID]) -> list[Component]:
        if not ids:
            return []
        result = await self.db.exec(select(Component).where(Component.id.in_(ids)))
        return list(result.all())

    async def count_distinct_names(
        self, statuses: frozenset[ComponentStatus] | None = None, kind: ComponentKind | None = None
    ) -> int:
        query = select(func.count(func.distinct(Component.name)))
        if statuses is not None:
            query = query.where(Component.status.in_(statuses))
        if kind is not None:
            query = query.where(Component.kind == kind)
        result = await self.db.exec(query)
        return result.one()

    async def count_distinct_contributors(self, statuses: frozenset[ComponentStatus] | None = None) -> int:
        query = select(func.count(func.distinct(Component.created_by_id))).where(Component.created_by_id.is_not(None))
        if statuses is not None:
            query = query.where(Component.status.in_(statuses))
        result = await self.db.exec(query)
        return result.one()

    async def find_by_id(self, component_id: uuid.UUID) -> Component | None:
        """The component with one composite level loaded - a workflow's steps and the
        components they run. The mapper's own lazy="selectin" cannot do that: eager loading
        stops where a path revisits a relationship (component -> steps -> component), so a
        step's child would be left to a lazy load, which an AsyncSession cannot do."""
        query = select(Component).where(Component.id == component_id).options(*_ONE_LEVEL)
        result = await self.db.exec(query)
        return result.first()

    async def find_by_id_fresh(self, component_id: uuid.UUID) -> Component | None:
        """Same as find_by_id, but repopulates a component already resident in the session -
        the reload after a write. Steps built from a foreign key alone (component_id set,
        the step.component relationship never loaded) stay unloaded on a plain identity-map
        hit, and accessing them later would attempt a genuine lazy load and crash with
        MissingGreenlet."""
        query = (
            select(Component)
            .where(Component.id == component_id)
            .options(*_ONE_LEVEL)
            .execution_options(populate_existing=True)
        )
        result = await self.db.exec(query)
        return result.first()

    async def load_tree(self, root: Component) -> Component:
        """Load the whole composite below `root`, one level per round trip, until no
        workflow is left unexpanded. Bounded by the tree's depth - cycles are rejected
        whenever a step is bound (see composite.tree.would_create_cycle), and a component
        reached twice is expanded once."""
        expanded: set[uuid.UUID] = set()
        frontier = [root]
        while frontier:
            ids = list({c.id for c in frontier if c.is_workflow and c.id not in expanded})
            if not ids:
                break
            expanded.update(ids)
            query = (
                select(Component)
                .where(Component.id.in_(ids))
                .options(*_ONE_LEVEL)
                .execution_options(populate_existing=True)
            )
            loaded = (await self.db.exec(query)).all()
            frontier = [child for component in loaded for child in component.children]
        return root

    async def find_ancestors(self, component_id: uuid.UUID) -> list[Component]:
        """Every workflow version nesting this exact version, at any depth, each once - the
        inverse of load_tree ("who runs me?" rather than "what do I run?"), one level per
        round trip. Steps pin a version row, so other versions of the lineage don't count."""
        found: dict[uuid.UUID, Component] = {}
        frontier = {component_id}
        while frontier:
            query = (
                select(Component)
                .join(Workflow, Workflow.component_id == Component.id)
                .join(WorkflowStep, WorkflowStep.workflow_id == Workflow.component_id)
                .where(WorkflowStep.component_id.in_(frontier))
                .distinct()
            )
            parents = [c for c in (await self.db.exec(query)).all() if c.id not in found]
            found.update((c.id, c) for c in parents)
            frontier = {c.id for c in parents}
        return list(found.values())

    async def find_versions_by_name(self, name: str) -> list[Component]:
        query = select(Component).where(Component.name == name).order_by(Component.version.asc())
        result = await self.db.exec(query)
        return list(result.all())

    async def find_latest_by_name(self, name: str) -> Component | None:
        query = select(Component).where(Component.name == name).order_by(Component.version.desc())
        result = await self.db.exec(query)
        return result.first()

    async def find_tool_by_repo_url(self, repo_url: str) -> Component | None:
        query = (
            select(Component)
            .join(Tool, Tool.component_id == Component.id)
            .where(Component.repo_url == repo_url)
            .order_by(Component.version.desc())
        )
        result = await self.db.exec(query)
        return result.first()

    async def rename_lineage(self, old_name: str, new_name: str) -> None:
        """Rename every version of a lineage at once, and the favorites keyed by it - the
        name is the lineage key, so renaming only one version would split the lineage."""
        require_unit_of_work(self.db)
        await self.db.exec(update(Component).where(Component.name == old_name).values(name=new_name))
        await self.db.exec(update(Favorite).where(Favorite.component_name == old_name).values(component_name=new_name))

    async def add(self, component: Component) -> Component:
        require_unit_of_work(self.db)
        self.db.add(component)
        await self.db.flush()
        return component

    async def add_all(self, components: list[Component]) -> None:
        require_unit_of_work(self.db)
        self.db.add_all(components)
        await self.db.flush()

    async def delete(self, component: Component) -> None:
        require_unit_of_work(self.db)
        await self.db.delete(component)
        await self.db.flush()
