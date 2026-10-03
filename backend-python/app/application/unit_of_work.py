from types import TracebackType
from typing import Protocol, Self

from app.domain.repository.components_repository import ComponentsRepository
from app.domain.repository.favorites_repository import FavoritesRepository
from app.domain.repository.login_codes_repository import LoginCodesRepository
from app.domain.repository.users_repository import UsersRepository
from app.domain.repository.workflow_draft_repository import WorkflowDraftRepository
from app.domain.repository.workflows_repository import WorkflowsRepository


class UnitOfWork(Protocol):
    """One use case's transaction, and the repositories that write inside it.

    Repositories only add, delete and flush - they never commit. The use case a router
    calls opens the unit (`async with uow:`), does all its writes and ends with
    `await uow.commit()`; anything raised before that rolls every write back, so a use
    case is applied completely or not at all.

    Boundaries are strict: entering a unit that is already open raises, so one use case
    never silently calls another one's commit. Helpers that write on behalf of an entry
    point simply run inside the caller's unit. Reads need no unit.
    """

    components: ComponentsRepository
    workflows: WorkflowsRepository
    favorites: FavoritesRepository
    drafts: WorkflowDraftRepository
    users: UsersRepository
    login_codes: LoginCodesRepository

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
