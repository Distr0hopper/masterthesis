from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.exception.handlers import register_exception_handlers
from app.api.util.endpoints import api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Component Repository API",
    description="REST API for managing CWL-based workflow components",
    version="1.0",
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
