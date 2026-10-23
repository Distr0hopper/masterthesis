"""Passwordless login over HTTP: request a code, log in with it, use and refresh the
token - and every way a code or token is refused."""

from datetime import UTC, datetime, timedelta

import httpx
import jwt
import pytest
from sqlmodel import select

from app.config import get_settings
from app.domain.models.user import User
from app.infrastructure.security.security import JWT_ALGORITHM
from tests.conftest import FakeEmailSender, SessionFactory
from tests.db_factories import bearer, save, user

pytestmark = pytest.mark.anyio

EMAIL = "someone@example.com"


async def log_in(client: httpx.AsyncClient, emails: FakeEmailSender, email: str = EMAIL) -> str:
    response = await client.post("/auth/otp/request", json={"email": email})
    assert response.status_code == 200
    assert response.json()["cooldownSeconds"] == get_settings().otp_request_cooldown
    to, code = emails.sent[-1]
    assert to == email

    response = await client.post("/auth/otp/verify", json={"email": email, "code": code})
    assert response.status_code == 200
    return response.json()["accessToken"]


async def users_with(sessions: SessionFactory, email: str) -> list[User]:
    async with sessions() as session:
        return list((await session.exec(select(User).where(User.email == email))).all())


async def test_a_new_email_logs_in_and_gets_an_account(
    client: httpx.AsyncClient, emails: FakeEmailSender, sessions: SessionFactory
) -> None:
    token = await log_in(client, emails)

    response = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == EMAIL
    assert len(await users_with(sessions, EMAIL)) == 1


async def test_logging_in_again_reuses_the_account(
    client: httpx.AsyncClient, emails: FakeEmailSender, sessions: SessionFactory
) -> None:
    existing = user(EMAIL)
    await save(sessions, existing)

    token = await log_in(client, emails)

    response = await client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.json()["id"] == str(existing.id)
    assert len(await users_with(sessions, EMAIL)) == 1


async def test_the_case_of_an_email_does_not_make_another_account(
    client: httpx.AsyncClient, emails: FakeEmailSender, sessions: SessionFactory
) -> None:
    existing = user(EMAIL)
    await save(sessions, existing)

    await client.post("/auth/otp/request", json={"email": "Someone@Example.com"})
    to, code = emails.sent[-1]
    assert to == EMAIL
    # the code reaches the account however the address is spelled at the second step
    response = await client.post("/auth/otp/verify", json={"email": "SOMEONE@example.com", "code": code})
    assert response.status_code == 200

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {response.json()['accessToken']}"})
    assert me.json()["id"] == str(existing.id)
    assert len(await users_with(sessions, EMAIL)) == 1


async def test_a_second_request_within_the_cooldown_is_429_with_retry_after(
    client: httpx.AsyncClient, emails: FakeEmailSender
) -> None:
    await client.post("/auth/otp/request", json={"email": EMAIL})
    response = await client.post("/auth/otp/request", json={"email": EMAIL})

    assert response.status_code == 429
    assert 0 < int(response.headers["Retry-After"]) <= get_settings().otp_request_cooldown
    assert len(emails.sent) == 1


async def test_a_wrong_code_and_a_used_code_are_401(client: httpx.AsyncClient, emails: FakeEmailSender) -> None:
    await client.post("/auth/otp/request", json={"email": EMAIL})
    _, code = emails.sent[-1]
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"

    assert (await client.post("/auth/otp/verify", json={"email": EMAIL, "code": wrong})).status_code == 401
    assert (await client.post("/auth/otp/verify", json={"email": EMAIL, "code": code})).status_code == 200
    assert (await client.post("/auth/otp/verify", json={"email": EMAIL, "code": code})).status_code == 401


async def test_the_attempt_limit_holds_across_requests(client: httpx.AsyncClient, emails: FakeEmailSender) -> None:
    await client.post("/auth/otp/request", json={"email": EMAIL})
    _, code = emails.sent[-1]
    wrong = f"{(int(code) + 1) % 1_000_000:06d}"

    for _ in range(get_settings().otp_max_attempts):
        await client.post("/auth/otp/verify", json={"email": EMAIL, "code": wrong})
    # even the right code is refused now - every failed attempt was committed
    assert (await client.post("/auth/otp/verify", json={"email": EMAIL, "code": code})).status_code == 401


@pytest.mark.parametrize(
    "body",
    [{"email": "not-an-email"}, {"email": EMAIL, "code": "12345"}, {"email": EMAIL, "code": "abcdef"}],
)
async def test_malformed_login_requests_are_422(client: httpx.AsyncClient, body: dict) -> None:
    path = "/auth/otp/verify" if "code" in body else "/auth/otp/request"
    assert (await client.post(path, json=body)).status_code == 422


async def test_a_valid_token_is_refreshed(client: httpx.AsyncClient, sessions: SessionFactory) -> None:
    owner = user()
    await save(sessions, owner)

    response = await client.post("/auth/refresh", headers=bearer(owner))
    assert response.status_code == 200
    refreshed = response.json()["accessToken"]
    assert (await client.get("/users/me", headers={"Authorization": f"Bearer {refreshed}"})).status_code == 200


def _token(sub: str, exp: datetime, secret: str | None = None) -> dict[str, str]:
    payload = {"sub": sub, "email": "x@example.com", "iat": exp - timedelta(hours=1), "exp": exp}
    token = jwt.encode(payload, secret or get_settings().jwt_secret, algorithm=JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


async def test_missing_expired_forged_and_orphaned_tokens_are_401(
    client: httpx.AsyncClient, sessions: SessionFactory
) -> None:
    owner = user()
    await save(sessions, owner)
    now = datetime.now(UTC)
    refused = {
        "missing": {},
        "garbage": {"Authorization": "Bearer not.a.jwt"},
        "expired": _token(str(owner.id), now - timedelta(seconds=1)),
        "forged": _token(str(owner.id), now + timedelta(hours=1), secret="another-secret-" * 4),
        "unknown user": _token("00000000-0000-0000-0000-000000000000", now + timedelta(hours=1)),
        "no uuid": _token("someone", now + timedelta(hours=1)),
    }

    for case, headers in refused.items():
        for method, path in (("GET", "/users/me"), ("POST", "/auth/refresh"), ("GET", "/components/mine")):
            response = await client.request(method, path, headers=headers)
            assert response.status_code == 401, f"{case} token on {method} {path}"


async def test_a_bad_token_on_a_public_endpoint_just_browses_anonymously(client: httpx.AsyncClient) -> None:
    response = await client.get("/components", headers={"Authorization": "Bearer not.a.jwt"})
    assert response.status_code == 200
