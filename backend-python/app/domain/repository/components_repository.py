import uuid
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends
from sqlmodel import and_, func, or_, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.component import Component, ComponentStatus
from app.domain.models.component_domain import DOMAIN_AGNOSTIC, ComponentDomain
from app.domain.models.favorite import Favorite, FavoriteEntityType
from app.domain.pagination.pagination import PaginatedList
from app.infrastructure.db.session import get_db


@dataclass
class ComponentListFilter:
    #: match components carrying ANY of these domains (union) - empty means no filter
    domains: list[str] = field(default_factory=list)
    created_by: uuid.UUID | None = None
    exclude_created_by: uuid.UUID | None = None
    favorited_by: uuid.UUID | None = None
    search: str | None = None
    status: ComponentStatus | None = None


class ComponentsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "ComponentsRepository":
        return ComponentsRepository(db)

    def _apply_filters(self, query, filter: ComponentListFilter):
        if filter.domains:
            matching = {*filter.domains, DOMAIN_AGNOSTIC}
            query = query.where(
                Component.id.in_(
                    select(ComponentDomain.component_id).where(ComponentDomain.domain.in_(matching))
                )
            )
        if filter.status is not None:
            query = query.where(Component.status == filter.status)
        if filter.created_by is not None:
            query = query.where(Component.created_by_id == filter.created_by)
        if filter.exclude_created_by is not None:
            query = query.where(
                or_(Component.created_by_id != filter.exclude_created_by, Component.created_by_id.is_(None))
            )
        if filter.favorited_by is not None:
            query = query.join(
                Favorite,
                and_(
                    Favorite.entity_type == FavoriteEntityType.COMPONENT,
                    Favorite.entity_ref == Component.name,
                    Favorite.user_id == filter.favorited_by,
                ),
            )
        if filter.search is not None:
            query = query.where(Component.name.ilike(f"%{filter.search}%"))
        return query

    async def find_all(self, status: ComponentStatus | None = None) -> list[Component]:
        query = select(Component).distinct(Component.name)
        if status is not None:
            query = query.where(Component.status == status)
        query = query.order_by(Component.name, Component.version.desc())
        result = await self.db.exec(query)
        return list(result.all())

    async def find_paginated(
        self, filter: ComponentListFilter, pagination: PaginatedList
    ) -> tuple[list[Component], int]:
        base_query = self._apply_filters(select(Component).distinct(Component.name), filter)

        count_query = select(func.count()).select_from(base_query.subquery())
        total = (await self.db.exec(count_query)).one()

        items_query = (
            base_query.order_by(Component.name, Component.version.desc())
            .limit(pagination.limit)
            .offset(pagination.offset)
        )
        result = await self.db.exec(items_query)
        return list(result.all()), total

    async def count_distinct_names(self, status: ComponentStatus | None = None) -> int:
        query = select(func.count(func.distinct(Component.name)))
        if status is not None:
            query = query.where(Component.status == status)
        result = await self.db.exec(query)
        return result.one()

    async def count_distinct_contributors(self, status: ComponentStatus | None = None) -> int:
        query = select(func.count(func.distinct(Component.created_by_id))).where(Component.created_by_id.is_not(None))
        if status is not None:
            query = query.where(Component.status == status)
        result = await self.db.exec(query)
        return result.one()

    async def find_by_id(self, component_id: uuid.UUID) -> Component | None:
        return await self.db.get(Component, component_id)

    async def find_versions_by_name(self, name: str) -> list[Component]:
        query = select(Component).where(Component.name == name).order_by(Component.version.asc())
        result = await self.db.exec(query)
        return list(result.all())

    async def find_by_repo_url(self, repo_url: str) -> Component | None:
        query = select(Component).where(Component.repo_url == repo_url).order_by(Component.version.desc())
        result = await self.db.exec(query)
        return result.first()

    async def exists_ontology_url(self, ontology_url: str) -> bool:
        query = select(Component.id).where(Component.ontology_url == ontology_url).limit(1)
        result = await self.db.exec(query)
        return result.first() is not None

    async def save(self, component: Component) -> Component:
        self.db.add(component)
        await self.db.commit()
        await self.db.refresh(component)
        return component

    async def delete(self, component: Component) -> None:
        await self.db.delete(component)
        await self.db.commit()