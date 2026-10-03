import uuid

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.user import User
from app.infrastructure.db.session import require_unit_of_work


class UsersRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_by_email(self, email: str) -> User | None:
        result = await self.db.exec(select(User).where(User.email == email))
        return result.first()

    async def find_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def add(self, user: User) -> User:
        require_unit_of_work(self.db)
        self.db.add(user)
        await self.db.flush()
        return user
