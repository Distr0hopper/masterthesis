import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends

from app.application.exception.otp_exceptions import OtpRequestRateLimitedError
from app.application.service.auth_service import AuthService
from app.domain.exception.login_code_exceptions import (
    InvalidOtpCodeError,
    OtpAttemptsExceededError,
    OtpCodeExpiredError,
)
from app.domain.models.login_code import LoginCode
from app.domain.models.user import User
from app.domain.repository.login_codes_repository import LoginCodesRepository
from app.domain.repository.users_repository import UsersRepository
from app.infrastructure.email.email_sender import EmailSender
from app.infrastructure.security.security import hash_secret, verify_secret
from app.config import get_settings

settings = get_settings()


class OtpService:
    def __init__(
        self,
        login_codes_repository: LoginCodesRepository,
        users_repository: UsersRepository,
        email_sender: EmailSender,
        auth_service: AuthService,
    ):
        self.login_codes_repository = login_codes_repository
        self.users_repository = users_repository
        self.email_sender = email_sender
        self.auth_service = auth_service

    @staticmethod
    def get_service(
        login_codes_repository: Annotated[LoginCodesRepository, Depends(LoginCodesRepository.get_repository)],
        users_repository: Annotated[UsersRepository, Depends(UsersRepository.get_repository)],
        email_sender: Annotated[EmailSender, Depends(EmailSender.get_sender)],
        auth_service: Annotated[AuthService, Depends(AuthService.get_service)],
    ) -> "OtpService":
        return OtpService(login_codes_repository, users_repository, email_sender, auth_service)

    async def request_code(self, email: str) -> int:
        now = datetime.now(timezone.utc)
        latest = await self.login_codes_repository.find_latest_by_email(email)
        if latest is not None and (now - latest.created_at) < timedelta(seconds=settings.otp_request_cooldown):
            retry_after = settings.otp_request_cooldown - int((now - latest.created_at).total_seconds())
            raise OtpRequestRateLimitedError(retry_after_seconds=retry_after)

        code = f"{secrets.randbelow(1_000_000):06d}"
        login_code = LoginCode(
            email=email,
            code_hash=hash_secret(code),
            expires_at=now + timedelta(seconds=settings.otp_expires_in),
        )
        await self.login_codes_repository.create(login_code)
        await self.email_sender.send_otp_email(email, code)
        return settings.otp_request_cooldown

    async def verify_code(self, email: str, code: str) -> tuple[str, int]:
        login_code = await self.login_codes_repository.find_latest_by_email(email)
        if login_code is None or login_code.consumed_at is not None:
            raise InvalidOtpCodeError()
        if login_code.attempts >= settings.otp_max_attempts:
            raise OtpAttemptsExceededError()
        if login_code.expires_at < datetime.now(timezone.utc):
            raise OtpCodeExpiredError()
        if not verify_secret(code, login_code.code_hash):
            login_code.attempts += 1
            await self.login_codes_repository.update(login_code)
            raise InvalidOtpCodeError()

        login_code.consumed_at = datetime.now(timezone.utc)
        await self.login_codes_repository.update(login_code)

        user = await self.users_repository.find_by_email(email)
        if user is None:
            user = await self.users_repository.create(User(email=email))

        return self.auth_service.issue_token(user)