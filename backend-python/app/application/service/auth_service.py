import uuid
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.exception.auth_exceptions import InvalidTokenError
from app.infrastructure.security.security import create_access_token, decode_access_token
from app.config import get_settings
from app.domain.models.user import User
from app.application.unit_of_work import UnitOfWork
from app.domain.repository.users_repository import UsersRepository
from app.infrastructure.db.unit_of_work import SqlUnitOfWork

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self, users_repository: UsersRepository):
        self.users_repository = users_repository

    @staticmethod
    def get_service(
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
    ) -> "AuthService":
        return AuthService(uow.users)

    @staticmethod
    async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
    ) -> User:
        if credentials is None:
            raise InvalidTokenError()
        return await AuthService(uow.users).get_user_from_token(credentials.credentials)

    @staticmethod
    async def get_current_user_optional(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
    ) -> User | None:
        if credentials is None:
            return None
        try:
            return await AuthService(uow.users).get_user_from_token(credentials.credentials)
        except InvalidTokenError:
            # anonymous browsing must never break because of a stale/garbage token
            return None

    def issue_token(self, user: User) -> tuple[str, int]:
        return create_access_token(subject=str(user.id), email=user.email), settings.jwt_expires_in

    async def get_user_from_token(self, token: str) -> User:
        try:
            payload = decode_access_token(token)
            user = await self.users_repository.find_by_id(uuid.UUID(payload["sub"]))
        except (pyjwt.PyJWTError, ValueError, KeyError):
            raise InvalidTokenError()

        if user is None:
            raise InvalidTokenError()
        return user