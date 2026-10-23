"""The scheduled purge of expired login codes: its SQL against Postgres, and the job as the
scheduler runs it - a process whose exit code says whether to retry."""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlmodel import select

from app.domain.models.login_code import LoginCode
from app.infrastructure.db.unit_of_work import SqlUnitOfWork
from tests.conftest import TEST_DATABASE, SessionFactory
from tests.db_factories import save

BACKEND = Path(__file__).resolve().parents[2]


def run_job(**env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "app.jobs.purge_login_codes"],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_NAME": TEST_DATABASE, **env},
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.mark.anyio
async def test_only_expired_codes_are_deleted(sessions: SessionFactory) -> None:
    now = datetime.now(UTC)
    await save(
        sessions,
        LoginCode(email="old@example.com", code_hash="x", expires_at=now - timedelta(minutes=1)),
        LoginCode(email="fresh@example.com", code_hash="x", expires_at=now + timedelta(minutes=9)),
    )

    async with sessions() as session:
        uow = SqlUnitOfWork(session)
        async with uow:
            deleted = await uow.login_codes.delete_expired(now)
            await uow.commit()

    assert deleted == 1
    async with sessions() as session:
        left = (await session.exec(select(LoginCode.email))).all()
    assert list(left) == ["fresh@example.com"]


def test_the_job_exits_0_after_a_run(database: str) -> None:
    result = run_job()
    assert result.returncode == 0, result.stderr
    assert "expired login code(s)" in result.stderr


def test_the_job_exits_1_when_the_database_is_unreachable() -> None:
    # a port nothing listens on - the scheduler must see the failure and retry
    result = run_job(DATABASE_PORT="1")
    assert result.returncode == 1
    assert "Purging expired login codes failed" in result.stderr
