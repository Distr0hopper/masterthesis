"""Fixtures for the tests that need a real Postgres: the repositories' SQL, the routers'
authorization and the HTTP mapping of every exception.

They run against their own database next to the dev one (same Compose Postgres on :5433,
`make docker-infra`), recreated and migrated once per run - the dev data is never touched.
Each test runs in one outer transaction that is rolled back afterwards; the units of work
inside commit to savepoints. Without a running Postgres those tests are skipped."""

import os

# before anything imports app.config - its settings, and the engine built from them, are
# cached at import time
TEST_DATABASE = "component_repository_test"
os.environ["DATABASE_NAME"] = TEST_DATABASE

import asyncio  # noqa: E402
from collections.abc import AsyncGenerator, Callable  # noqa: E402
from pathlib import Path  # noqa: E402

import asyncpg  # noqa: E402
import httpx  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402
from sqlmodel.ext.asyncio.session import AsyncSession  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.infrastructure.email.email_sender import EmailSender  # noqa: E402

SessionFactory = Callable[[], AsyncSession]


class FakeEmailSender(EmailSender):
    """Keeps every login code it was asked to send, so a test can log in with it."""

    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    async def send_otp_email(self, to: str, code: str) -> None:
        self.sent.append((to, code))


async def _recreate_database() -> None:
    settings = get_settings()
    assert settings.database_name == TEST_DATABASE, "refusing to recreate anything but the test database"
    connection = await asyncpg.connect(
        host=settings.database_host,
        port=settings.database_port,
        user=settings.database_user,
        password=settings.database_password,
        database="postgres",
        timeout=3,
    )
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{TEST_DATABASE}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{TEST_DATABASE}"')
    finally:
        await connection.close()


@pytest.fixture(scope="session")
def database() -> str:
    """The migrated test database's URL - a fresh `alembic upgrade head` from nothing, so
    every run also checks that the migrations build the schema from scratch."""
    try:
        asyncio.run(_recreate_database())
    except (OSError, asyncpg.PostgresError, TimeoutError) as error:
        pytest.skip(f"no Postgres for the database tests (make docker-infra): {error}")

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(config, "head")
    return get_settings().database_url


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def connection(database: str) -> AsyncGenerator[AsyncConnection, None]:
    engine = create_async_engine(database, poolclass=NullPool)
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.fixture
def sessions(connection: AsyncConnection) -> SessionFactory:
    """A new session per call, like one per request - all inside the test's transaction,
    with every commit going to a savepoint."""

    def new_session() -> AsyncSession:
        return AsyncSession(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")

    return new_session


@pytest.fixture
def emails() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
async def client(sessions: SessionFactory, emails: FakeEmailSender) -> AsyncGenerator[httpx.AsyncClient, None]:
    from app.infrastructure.db.session import get_db
    from app.main import app

    async def test_db() -> AsyncGenerator[AsyncSession, None]:
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[EmailSender.get_sender] = lambda: emails
    # ASGITransport runs no lifespan - the app's startup migrations stay out of it
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
