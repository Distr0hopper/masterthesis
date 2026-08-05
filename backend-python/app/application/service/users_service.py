from typing import Annotated

from fastapi import Depends

from app.domain.models.user import User
from app.domain.repository.users_repository import UsersRepository


class UsersService:
    def __init__(self, users_repository: UsersRepository):
        self.users_repository = users_repository

    @staticmethod
    def get_service(
        users_repository: Annotated[UsersRepository, Depends(UsersRepository.get_repository)],
    ) -> "UsersService":
        return UsersService(users_repository)

    async def update_user(self, user: User) -> User:
        return await self.users_repository.update(user)