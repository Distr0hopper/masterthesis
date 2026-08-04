import uuid
from typing import Annotated

import jwt as pyjwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.exception.auth_exceptions import InvalidCredentialsError, InvalidTokenError
from app.infrastructure.security.security import create_access_token, decode_access_token, hash_password, verify_password
from app.config import get_settings
from app.domain.exception.user_exceptions import EmailAlreadyRegisteredError
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

    async def validate_user(self, email: str, password: str) -> User:
        user = await self.users_repository.find_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        return user

    async def register(self, email: str, first_name: str, last_name: str, password: str) -> User:
        existing = await self.users_repository.find_by_email(email)
        if existing is not None:
            raise EmailAlreadyRegisteredError()

        user = User(
            email=email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
        )
        return await self.users_repository.create(user)

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
