from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.login_code import LoginCode
from app.infrastructure.db.session import require_unit_of_work


class LoginCodesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def find_latest_by_email(self, email: str) -> LoginCode | None:
        query = select(LoginCode).where(LoginCode.email == email).order_by(LoginCode.created_at.desc())
        result = await self.db.exec(query)
        return result.first()

    async def add(self, login_code: LoginCode) -> LoginCode:
        require_unit_of_work(self.db)
        self.db.add(login_code)
        await self.db.flush()
        return login_code