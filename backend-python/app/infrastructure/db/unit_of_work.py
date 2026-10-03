from types import TracebackType
from typing import Annotated, Self

from fastapi import Depends
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.repository.components_repository import ComponentsRepository
from app.domain.repository.favorites_repository import FavoritesRepository
from app.domain.repository.login_codes_repository import LoginCodesRepository
from app.domain.repository.users_repository import UsersRepository
from app.domain.repository.workflow_draft_repository import WorkflowDraftRepository
from app.domain.repository.workflows_repository import WorkflowsRepository
from app.infrastructure.db.session import UOW_ACTIVE, UOW_WRITTEN, get_db


class SqlUnitOfWork:
    """The UnitOfWork over the request's session - see app.application.unit_of_work."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.components = ComponentsRepository(session)
        self.workflows = WorkflowsRepository(session)
        self.favorites = FavoritesRepository(session)
        self.drafts = WorkflowDraftRepository(session)
        self.users = UsersRepository(session)
        self.login_codes = LoginCodesRepository(session)

    @staticmethod
    def get_unit_of_work(session: Annotated[AsyncSession, Depends(get_db)]) -> "SqlUnitOfWork":
        # FastAPI caches a dependency per request, so every service of one request shares
        # this instance - which is what lets __aenter__ detect a nested use case
        return SqlUnitOfWork(session)

    async def __aenter__(self) -> Self:
        if self.session.info.get(UOW_ACTIVE):
            raise RuntimeError("unit of work is already open - a use case must not call another use case")
        self.session.info[UOW_ACTIVE] = True
        self.session.info[UOW_WRITTEN] = False
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.session.info[UOW_ACTIVE] = False
        if exc_type is not None:
            await self.rollback()
        elif self.session.info.get(UOW_WRITTEN):
            await self.rollback()
            raise RuntimeError("use case ended with uncommitted writes - they were rolled back")
        # otherwise committed, or nothing written (e.g. publishing what already is
        # published) - no rollback then, since that would expire every loaded object the
        # router is about to serialise

    async def commit(self) -> None:
        await self.session.commit()
        self.session.info[UOW_WRITTEN] = False

    async def rollback(self) -> None:
        await self.session.rollback()
