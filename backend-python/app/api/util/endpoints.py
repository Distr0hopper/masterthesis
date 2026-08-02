from fastapi import APIRouter

from app.api.routers.auth_router import router as auth_router
from app.api.routers.domains_router import router as domains_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(domains_router)
