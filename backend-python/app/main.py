import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception.handlers import register_exception_handlers
from app.api.util.endpoints import api_router
from app.config import get_settings
from app.infrastructure.db.migrations import run_migrations

logging.basicConfig(level=logging.INFO)
# alembic.ini sets the root logger to WARNING; give our own logger namespace an
# explicit level so it's unaffected once alembic's env.py re-applies that config.
logging.getLogger("app").setLevel(logging.INFO)
logger = logging.getLogger("app.main")

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    await run_migrations()
    logger.info(f"Swagger UI available at http://localhost:{settings.port}/docs")
    yield


app = FastAPI(
    title="Component Repository API",
    description="REST API for managing CWL-based workflow components",
    version="1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.cors_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
    max_age=3600,
)

register_exception_handlers(app)
app.include_router(api_router)