import uuid
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.exception.auth_exceptions import InvalidTokenError
from app.infrastructure.security.security import create_access_token, decode_access_token
from app.config import get_settings
from app.domain.models.user import User
from app.domain.repository.users_repository import UsersRepository

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)


class AuthService:
    def __init__(self, users_repository: UsersRepository):
        self.users_repository = users_repository

    @staticmethod
    def get_service(
        users_repository: Annotated[UsersRepository, Depends(UsersRepository.get_repository)],
    ) -> "AuthService":
        return AuthService(users_repository)

    @staticmethod
    async def get_current_user(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
        users_repository: Annotated[UsersRepository, Depends(UsersRepository.get_repository)],
    ) -> User:
        if credentials is None:
            raise InvalidTokenError()
        return await AuthService(users_repository).get_user_from_token(credentials.credentials)

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