"""SqlUnitOfWork's boundaries, against a stand-in session - no database needed."""

import asyncio

import pytest

from app.infrastructure.db.session import require_unit_of_work
from app.infrastructure.db.unit_of_work import SqlUnitOfWork


class FakeSession:
    def __init__(self):
        self.info: dict = {}
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


def uow() -> tuple[SqlUnitOfWork, FakeSession]:
    session = FakeSession()
    return SqlUnitOfWork(session), session  # type: ignore[arg-type]


def test_a_committed_unit_neither_rolls_back_nor_complains() -> None:
    unit, session = uow()

    async def use_case() -> None:
        async with unit:
            require_unit_of_work(session)  # type: ignore[arg-type]
            await unit.commit()

    asyncio.run(use_case())
    assert (session.commits, session.rollbacks) == (1, 0)


def test_an_error_rolls_everything_back() -> None:
    unit, session = uow()

    async def use_case() -> None:
        async with unit:
            require_unit_of_work(session)  # type: ignore[arg-type]
            raise ValueError("boom")

    with pytest.raises(ValueError):
        asyncio.run(use_case())
    assert (session.commits, session.rollbacks) == (0, 1)


def test_writes_left_uncommitted_are_rolled_back_loudly() -> None:
    unit, session = uow()

    async def use_case() -> None:
        async with unit:
            require_unit_of_work(session)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="uncommitted writes"):
        asyncio.run(use_case())
    assert session.rollbacks == 1


def test_a_write_after_the_commit_counts_as_uncommitted() -> None:
    unit, session = uow()

    async def use_case() -> None:
        async with unit:
            await unit.commit()
            require_unit_of_work(session)  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="uncommitted writes"):
        asyncio.run(use_case())


def test_a_unit_that_wrote_nothing_needs_no_commit_and_keeps_loaded_objects() -> None:
    unit, session = uow()

    async def use_case() -> None:
        async with unit:
            pass

    asyncio.run(use_case())
    # a rollback would expire every loaded object the router is about to serialise
    assert (session.commits, session.rollbacks) == (0, 0)


def test_units_do_not_nest() -> None:
    unit, _ = uow()

    async def use_case() -> None:
        async with unit:
            async with unit:
                pass

    with pytest.raises(RuntimeError, match="already open"):
        asyncio.run(use_case())


def test_a_repository_write_outside_a_unit_is_refused() -> None:
    _, session = uow()
    with pytest.raises(RuntimeError, match="outside a unit of work"):
        require_unit_of_work(session)  # type: ignore[arg-type]
