import uuid
from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.user import User
from app.infrastructure.db.session import get_db


class UsersRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "UsersRepository":
        return UsersRepository(db)

    async def find_by_email(self, email: str) -> User | None:
        result = await self.db.exec(select(User).where(User.email == email))
        return result.first()

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def create(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
