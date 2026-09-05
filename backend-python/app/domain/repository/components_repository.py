import uuid
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlmodel import and_, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.component import Component
from app.domain.models.favorite import Favorite
from app.domain.pagination.pagination import PaginatedList
from app.infrastructure.db.session import get_db


@dataclass
class ComponentListFilter:
    domain: str | None = None
    exclude_created_by: uuid.UUID | None = None
    favorited_by: uuid.UUID | None = None
    search: str | None = None


class ComponentsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "ComponentsRepository":
        return ComponentsRepository(db)

    def _apply_filters(self, query, filter: ComponentListFilter):
        if filter.domain is not None:
            query = query.where(Component.domain == filter.domain)
        if filter.exclude_created_by is not None:
            # created_by_id IS NULL must still pass through - a plain `!=` comparison
            # against NULL is neither true nor false in SQL, so those rows would
            # otherwise be silently dropped instead of just not being excluded
            query = query.where(
                or_(Component.created_by_id != filter.exclude_created_by, Component.created_by_id.is_(None))
            )
        if filter.favorited_by is not None:
            # INNER JOIN, not a Python-side post-filter: needed so `total`/pagination
            # reflect the favorited-only count, not the unfiltered one. Safe to combine
            # with DISTINCT ON (name) below - Favorite's (user_id, component_name)
            # composite PK guarantees at most one matching row per (component, user),
            # so this can't fan out/duplicate rows ahead of the dedup.
            query = query.join(
                Favorite,
                and_(Favorite.component_name == Component.name, Favorite.user_id == filter.favorited_by),
            )
        if filter.search is not None:
            query = query.where(Component.name.ilike(f"%{filter.search}%"))
        return query

    async def find_all(self) -> list[Component]:
        # DISTINCT ON (name) + ORDER BY name, version DESC keeps only the latest version
        # of each lineage - browsing should show one card per component, not per version.
        # Only backs get_latest_components/create_from_zip now; the paginated browse/mine
        # endpoints go through find_paginated/find_paginated_by_created_by instead.
        query = select(Component).distinct(Component.name).order_by(Component.name, Component.version.desc())
        result = await self.db.exec(query)
        return list(result.all())

    async def find_paginated(
        self, filter: ComponentListFilter, pagination: PaginatedList
    ) -> tuple[list[Component], int]:
        base_query = self._apply_filters(select(Component).distinct(Component.name), filter)

        # count from the deduped-and-filtered subquery, without its ORDER BY - DISTINCT ON
        # requires the ORDER BY to lead with (name, version desc), but that ordering is
        # meaningless (and unnecessary work) inside a bare `SELECT count(*) FROM (...)`
        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.exec(count_query)).one()

        items_query = (
            base_query.order_by(Component.name, Component.version.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        result = await self.db.exec(items_query)
        return list(result.all()), total

    async def find_paginated_by_created_by(
        self, created_by_id: uuid.UUID, pagination: PaginatedList
    ) -> tuple[list[Component], int]:
        base_query = select(Component).distinct(Component.name).where(Component.created_by_id == created_by_id)

        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.exec(count_query)).one()

        items_query = (
            base_query.order_by(Component.name, Component.version.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        result = await self.db.exec(items_query)
        return list(result.all()), total

    async def count_distinct_names(self) -> int:
        result = await self.db.exec(select(func.count(func.distinct(Component.name))))
        return result.one()

    async def count_distinct_contributors(self) -> int:
        result = await self.db.exec(
            select(func.count(func.distinct(Component.created_by_id))).where(Component.created_by_id.is_not(None))
        )
        return result.one()

    async def find_by_id(self, component_id: uuid.UUID) -> Component | None:
        return await self.db.get(Component, component_id)

    async def find_versions_by_name(self, name: str) -> list[Component]:
        query = select(Component).where(Component.name == name).order_by(Component.version.asc())
        result = await self.db.exec(query)
        return list(result.all())

    async def find_by_repo_url(self, repo_url: str) -> Component | None:
        # ordered by version desc so callers reliably get the latest version of the
        # lineage, not an arbitrary one - a lineage can have many rows sharing this repo_url
        query = select(Component).where(Component.repo_url == repo_url).order_by(Component.version.desc())
        result = await self.db.exec(query)
        return result.first()

    async def save(self, component: Component) -> Component:
        self.db.add(component)
        await self.db.commit()
        await self.db.refresh(component)
        return component

    async def delete(self, component: Component) -> None:
        await self.db.delete(component)
        await self.db.commit()