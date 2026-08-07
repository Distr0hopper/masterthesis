import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.favorite import Favorite
from app.infrastructure.db.session import get_db


class FavoritesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "FavoritesRepository":
        return FavoritesRepository(db)

    async def add(self, user_id: uuid.UUID, component_name: str) -> None:
        # ON CONFLICT DO NOTHING on the composite PK - idempotent insert without a
        # check-then-insert race between two rapid double-clicks
        stmt = pg_insert(Favorite).values(user_id=user_id, component_name=component_name)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "component_name"])
        await self.db.exec(stmt)
        await self.db.commit()

    async def remove(self, user_id: uuid.UUID, component_name: str) -> None:
        favorite = await self.db.get(Favorite, (user_id, component_name))
        if favorite is not None:
            await self.db.delete(favorite)
            await self.db.commit()

    async def find_favorited_component_names(self, user_id: uuid.UUID) -> set[str]:
        query = select(Favorite.component_name).where(Favorite.user_id == user_id)
        result = await self.db.exec(query)
        return set(result.all())

    async def delete_by_component_name(self, component_name: str) -> None:
        # sweeps every user's favorite for this lineage - called when its last version is
        # deleted, since there's no FK to cascade this (component_name isn't unique on
        # components, so it can't be a real FK) and an orphaned row would otherwise be
        # unreachable via the API (favoriting/unfavoriting both resolve through a live component)
        stmt = delete(Favorite).where(Favorite.component_name == component_name)
        await self.db.exec(stmt)
        await self.db.commit()