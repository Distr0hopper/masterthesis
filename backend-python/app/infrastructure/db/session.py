from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

#: session.info keys: a unit of work is open on the session / it has written something
UOW_ACTIVE = "uow_active"
UOW_WRITTEN = "uow_written"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


def require_unit_of_work(db: AsyncSession) -> None:
    """Guard for every repository write: outside an open unit of work nothing would ever
    commit it, and the write would be dropped silently when the request's session closes."""
    if not db.info.get(UOW_ACTIVE):
        raise RuntimeError("repository write outside a unit of work - open one with `async with uow:`")
    db.info[UOW_WRITTEN] = True
