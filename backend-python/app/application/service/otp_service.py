import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends

from app.application.exception.otp_exceptions import OtpRequestRateLimitedError
from app.application.service.auth_service import AuthService
from app.application.unit_of_work import UnitOfWork
from app.domain.exception.login_code_exceptions import (
    InvalidOtpCodeError,
    OtpAttemptsExceededError,
    OtpCodeExpiredError,
)
from app.domain.models.login_code import LoginCode
from app.domain.models.user import User
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from app.infrastructure.email.email_sender import EmailSender
from app.infrastructure.security.security import hash_secret, verify_secret
from app.config import get_settings

settings = get_settings()


class OtpService:
    def __init__(self, uow: UnitOfWork, email_sender: EmailSender, auth_service: AuthService):
        self.uow = uow
        self.email_sender = email_sender
        self.auth_service = auth_service

    @staticmethod
    def get_service(
        uow: Annotated[UnitOfWork, Depends(SqlUnitOfWork.get_unit_of_work)],
        email_sender: Annotated[EmailSender, Depends(EmailSender.get_sender)],
        auth_service: Annotated[AuthService, Depends(AuthService.get_service)],
    ) -> "OtpService":
        return OtpService(uow, email_sender, auth_service)

    async def request_code(self, email: str) -> int:
        now = datetime.now(timezone.utc)
        latest = await self.uow.login_codes.find_latest_by_email(email)
        if latest is not None and (now - latest.created_at) < timedelta(seconds=settings.otp_request_cooldown):
            retry_after = settings.otp_request_cooldown - int((now - latest.created_at).total_seconds())
            raise OtpRequestRateLimitedError(retry_after_seconds=retry_after)

        code = f"{secrets.randbelow(1_000_000):06d}"
        login_code = LoginCode(
            email=email,
            code_hash=hash_secret(code),
            expires_at=now + timedelta(seconds=settings.otp_expires_in),
        )
        # committed before sending, so the cooldown holds even when the email fails
        async with self.uow:
            await self.uow.login_codes.add(login_code)
            await self.uow.commit()
        await self.email_sender.send_otp_email(email, code)
        return settings.otp_request_cooldown

    async def verify_code(self, email: str, code: str) -> tuple[str, int]:
        login_code = await self.uow.login_codes.find_latest_by_email(email)
        if login_code is None or login_code.consumed_at is not None:
            raise InvalidOtpCodeError()
        if login_code.attempts >= settings.otp_max_attempts:
            raise OtpAttemptsExceededError()
        if login_code.expires_at < datetime.now(timezone.utc):
            raise OtpCodeExpiredError()
        if not verify_secret(code, login_code.code_hash):
            # committed before raising - rolled back with the error, the failed attempt
            # would never count and the attempt limit would not stop brute-forcing
            async with self.uow:
                login_code.attempts += 1
                await self.uow.login_codes.add(login_code)
                await self.uow.commit()
            raise InvalidOtpCodeError()

        async with self.uow:
            login_code.consumed_at = datetime.now(timezone.utc)
            await self.uow.login_codes.add(login_code)
            user = await self.uow.users.find_by_email(email)
            if user is None:
                user = await self.uow.users.add(User(email=email))
            await self.uow.commit()

        return self.auth_service.issue_token(user)