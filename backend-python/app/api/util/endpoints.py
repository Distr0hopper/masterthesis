from fastapi import APIRouter

from app.api.routers.auth_router import router as auth_router
from app.api.routers.components_router import router as components_router
from app.api.routers.domains_router import router as domains_router
from app.api.routers.health_router import router as health_router
from app.api.routers.stats_router import router as stats_router
from app.api.routers.users_router import router as users_router
from app.api.routers.workflows_router import router as workflows_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(domains_router)
api_router.include_router(components_router)
api_router.include_router(stats_router)
api_router.include_router(workflows_router)
