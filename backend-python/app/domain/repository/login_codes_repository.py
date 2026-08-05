from typing import Annotated

from fastapi import Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.models.login_code import LoginCode
from app.infrastructure.db.session import get_db


class LoginCodesRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def get_repository(db: Annotated[AsyncSession, Depends(get_db)]) -> "LoginCodesRepository":
        return LoginCodesRepository(db)

    async def find_latest_by_email(self, email: str) -> LoginCode | None:
        query = select(LoginCode).where(LoginCode.email == email).order_by(LoginCode.created_at.desc())
        result = await self.db.exec(query)
        return result.first()

    async def create(self, login_code: LoginCode) -> LoginCode:
        self.db.add(login_code)
        await self.db.commit()
        await self.db.refresh(login_code)
        return login_code

    async def update(self, login_code: LoginCode) -> LoginCode:
        self.db.add(login_code)
        await self.db.commit()
        await self.db.refresh(login_code)
        return login_code