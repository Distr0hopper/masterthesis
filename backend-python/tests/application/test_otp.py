"""Login codes: at most one per email, a failed attempt counts even though the request
fails, and a code logs in only once."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.application.exception.otp_exceptions import OtpRequestRateLimitedError
from app.application.service.otp_service import OtpService
from app.domain.exception.login_code_exceptions import InvalidOtpCodeError
from app.domain.models.login_code import LoginCode
from app.domain.models.user import User
from app.infrastructure.security.security import hash_secret
from tests.application.fake_unit_of_work import FakeUnitOfWork

EMAIL = "a@b.c"


class FakeLoginCodesRepository:
    """The login_codes table, in memory: the latest code per email wins, like the real query."""

    def __init__(self, *codes: LoginCode):
        self.codes = list(codes)

    async def find_latest_by_email(self, email: str) -> LoginCode | None:
        own = [c for c in self.codes if c.email == email]
        return max(own, key=lambda c: c.created_at) if own else None

    async def add(self, login_code: LoginCode) -> LoginCode:
        if login_code not in self.codes:
            # the server default, which the real flush fetches back
            login_code.created_at = login_code.created_at or datetime.now(UTC)
            self.codes.append(login_code)
        return login_code

    async def delete_by_email(self, email: str) -> None:
        self.codes = [c for c in self.codes if c.email != email]


class FakeUsersRepository:
    async def find_by_email(self, email: str) -> User | None:
        return None

    async def add(self, user: User) -> User:
        return user


class FakeAuthService:
    def issue_token(self, user: User) -> tuple[str, int]:
        return "token", 3600


class FakeEmailSender:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_otp_email(self, email: str, code: str) -> None:
        self.sent.append((email, code))


def login_code(code: str = "123456", email: str = EMAIL, age: timedelta = timedelta(0)) -> LoginCode:
    created = datetime.now(UTC) - age
    return LoginCode(email=email, code_hash=hash_secret(code), expires_at=created + timedelta(minutes=10), created_at=created)


def service_with(*codes: LoginCode) -> tuple[OtpService, FakeUnitOfWork, FakeEmailSender]:
    uow = FakeUnitOfWork(login_codes=FakeLoginCodesRepository(*codes), users=FakeUsersRepository())
    sender = FakeEmailSender()
    return OtpService(uow, sender, FakeAuthService()), uow, sender  # type: ignore[arg-type]


def test_a_wrong_code_commits_the_attempt_before_failing() -> None:
    code = login_code()
    service, uow, _ = service_with(code)

    with pytest.raises(InvalidOtpCodeError):
        asyncio.run(service.verify_code(EMAIL, "000000"))

    assert code.attempts == 1
    assert (uow.commits, uow.rollbacks) == (1, 0)


def test_a_new_code_replaces_the_earlier_ones() -> None:
    # two minutes old - past the cooldown, still valid
    earlier = login_code("111111", age=timedelta(minutes=2))
    other_email = login_code("222222", email="x@y.z", age=timedelta(minutes=2))
    service, uow, sender = service_with(earlier, other_email)

    asyncio.run(service.request_code(EMAIL))

    [(_, new_code)] = sender.sent
    remaining = uow.login_codes.codes
    assert [c.email for c in remaining] == ["x@y.z", EMAIL]
    # the earlier code no longer logs in, although it hadn't expired - the new one does
    with pytest.raises(InvalidOtpCodeError):
        asyncio.run(service.verify_code(EMAIL, "111111"))
    assert asyncio.run(service.verify_code(EMAIL, new_code)) == ("token", 3600)


def test_the_cooldown_keeps_the_latest_code() -> None:
    latest = login_code(age=timedelta(seconds=10))
    service, uow, sender = service_with(latest)

    with pytest.raises(OtpRequestRateLimitedError):
        asyncio.run(service.request_code(EMAIL))

    assert uow.login_codes.codes == [latest]
    assert sender.sent == []


def test_a_code_logs_in_only_once() -> None:
    service, uow, _ = service_with(login_code("123456"))

    assert asyncio.run(service.verify_code(EMAIL, "123456")) == ("token", 3600)

    assert uow.login_codes.codes == []
    with pytest.raises(InvalidOtpCodeError):
        asyncio.run(service.verify_code(EMAIL, "123456"))
