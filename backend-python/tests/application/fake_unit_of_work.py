"""An in-memory stand-in for SqlUnitOfWork: same strict boundaries, plus counters so a
test can assert what a use case committed."""

from types import TracebackType
from typing import Any, Self


class FakeUnitOfWork:
    def __init__(
        self,
        components: Any = None,
        workflows: Any = None,
        favorites: Any = None,
        drafts: Any = None,
        users: Any = None,
        login_codes: Any = None,
    ):
        self.components = components
        self.workflows = workflows
        self.favorites = favorites
        self.drafts = drafts
        self.users = users
        self.login_codes = login_codes
        self.active = False
        self.commits = 0
        self.rollbacks = 0

    async def __aenter__(self) -> Self:
        if self.active:
            raise RuntimeError("unit of work is already open")
        self.active = True
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.active = False
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        assert self.active, "commit outside a unit of work"
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1
