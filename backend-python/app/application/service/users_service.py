from typing import Annotated

from fastapi import Depends

from app.application.unit_of_work import UnitOfWork
from app.domain.models.user import User
from app.infrastructure.db.unit_of_work import SqlUnitOfWork


class UsersService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    @staticmethod
    def get_service(
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
    ) -> "UsersService":
        return UsersService(uow)

    async def update_user(self, user: User) -> User:
        async with self.uow:
            await self.uow.users.add(user)
            await self.uow.commit()
        return user
