"""Login codes: a failed attempt has to count even though the request fails."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.application.service.otp_service import OtpService
from app.domain.exception.login_code_exceptions import InvalidOtpCodeError
from app.domain.models.login_code import LoginCode
from app.infrastructure.security.security import hash_secret
from tests.application.fake_unit_of_work import FakeUnitOfWork


class FakeLoginCodesRepository:
    def __init__(self, login_code: LoginCode):
        self.login_code = login_code

    async def find_latest_by_email(self, email: str) -> LoginCode | None:
        return self.login_code

    async def add(self, login_code: LoginCode) -> LoginCode:
        return login_code


def test_a_wrong_code_commits_the_attempt_before_failing() -> None:
    login_code = LoginCode(
        email="a@b.c",
        code_hash=hash_secret("123456"),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
        created_at=datetime.now(UTC),
    )
    uow = FakeUnitOfWork(login_codes=FakeLoginCodesRepository(login_code))
    service = OtpService(uow, None, None)  # type: ignore[arg-type]

    with pytest.raises(InvalidOtpCodeError):
        asyncio.run(service.verify_code("a@b.c", "000000"))

    assert login_code.attempts == 1
    assert (uow.commits, uow.rollbacks) == (1, 0)
