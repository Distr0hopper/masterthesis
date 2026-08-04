from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.infrastructure.db.session import get_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def check(db: Annotated[AsyncSession, Depends(get_db)]) -> JSONResponse:
    try:
        await db.exec(select(1))
    except Exception:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "database": "unreachable"},
        )
    return JSONResponse(content={"status": "ok", "database": "connected"})