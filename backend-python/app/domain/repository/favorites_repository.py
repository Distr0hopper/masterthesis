import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.favorite import Favorite, FavoriteEntityType
from app.infrastructure.db.session import get_db


class FavoritesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "FavoritesRepository":
        return FavoritesRepository(db)

    async def add(self, user_id: uuid.UUID, entity_type: FavoriteEntityType, entity_ref: str) -> None:
        # ON CONFLICT DO NOTHING on the composite PK - idempotent insert without a
        # check-then-insert race between two rapid double-clicks
        stmt = pg_insert(Favorite).values(user_id=user_id, entity_type=entity_type, entity_ref=entity_ref)
        stmt = stmt.on_conflict_do_nothing(index_elements=["user_id", "entity_type", "entity_ref"])
        await self.db.exec(stmt)
        await self.db.commit()

    async def remove(self, user_id: uuid.UUID, entity_type: FavoriteEntityType, entity_ref: str) -> None:
        favorite = await self.db.get(Favorite, (user_id, entity_type, entity_ref))
        if favorite is not None:
            await self.db.delete(favorite)
            await self.db.commit()

    async def find_favorited_refs(self, user_id: uuid.UUID, entity_type: FavoriteEntityType) -> set[str]:
        query = select(Favorite.entity_ref).where(
            Favorite.user_id == user_id, Favorite.entity_type == entity_type
        )
        result = await self.db.exec(query)
        return set(result.all())

    async def delete_by_ref(self, entity_type: FavoriteEntityType, entity_ref: str) -> None:
        # sweeps every user's favorite for this entity - there's no FK to cascade it
        # (entity_ref is polymorphic, so it can't be one) and an orphaned row would
        # otherwise be unreachable via the API, since favoriting and unfavoriting both
        # resolve through a live entity
        stmt = delete(Favorite).where(Favorite.entity_type == entity_type, Favorite.entity_ref == entity_ref)
        await self.db.exec(stmt)
        await self.db.commit()
