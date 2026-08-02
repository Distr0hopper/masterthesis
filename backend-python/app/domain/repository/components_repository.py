import uuid

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.component import Component
from app.infrastructure.db.session import get_db


class ComponentsRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: AsyncSession = Depends(get_db)) -> "ComponentsRepository":
        return ComponentsRepository(db)

    async def find_all(self, domain: str | None = None) -> list[Component]:
        query = select(Component)
        if domain is not None:
            query = query.where(Component.domain == domain)
        result = await self.db.exec(query)
        return list(result.all())

    async def find_by_id(self, component_id: uuid.UUID) -> Component | None:
        return await self.db.get(Component, component_id)

    async def find_versions_by_name(self, name: str) -> list[Component]:
        query = select(Component).where(Component.name == name).order_by(Component.version.asc())
        result = await self.db.exec(query)
        return list(result.all())