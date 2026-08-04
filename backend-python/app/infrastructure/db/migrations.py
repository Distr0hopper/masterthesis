"""Database migration utilities."""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config import get_settings

logger = logging.getLogger("app.infrastructure.db.migrations")


def _run_migrations_sync() -> None:
    """Run migrations synchronously in a thread (avoids async context conflicts)."""
    alembic_ini_path = Path.cwd() / "alembic.ini"
    if not alembic_ini_path.exists():
        logger.error(f"Alembic configuration not found: {alembic_ini_path}")
        raise FileNotFoundError(f"Alembic configuration not found: {alembic_ini_path}")

    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("sqlalchemy.url", get_settings().database_url)

    # Use command.upgrade() which will call alembic/env.py
    # This runs in a separate thread, so asyncio.run() won't conflict
    command.upgrade(alembic_cfg, "head")


async def _run_migrations_async() -> None:
    """Run migrations using thread pool to avoid async context conflicts."""
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        await loop.run_in_executor(executor, _run_migrations_sync)


async def run_migrations() -> None:
    """
    Run database migrations on startup using Alembic's Python API.

    Uses Alembic's native command API to upgrade database to the latest revision.
    Migrations run automatically on application startup if AUTO_MIGRATE is enabled.
    """
    settings = get_settings()
    if not settings.auto_migrate:
        logger.info("Auto-migration is disabled. Skipping migrations.")
        return

    try:
        logger.info("Running database migrations...")

        max_retries = 5
        retry_count = 0

        while retry_count < max_retries:
            try:
                await _run_migrations_async()
                logger.info("Database migrations completed successfully")
                return
            except Exception as e:
                error_msg = str(e)

                if "Can't locate revision identified by" in error_msg:
                    logger.warning(
                        "Database appears to be uninitialized. Creating initial migration may be needed."
                    )
                    return

                logger.warning(f"Migration attempt {retry_count + 1} failed: {error_msg}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(2)

        logger.error("Failed to run database migrations after multiple attempts")
        if not settings.is_prod:
            logger.warning(
                "Continuing startup despite migration failures (non-production environment)"
            )
        else:
            raise RuntimeError("Database migrations failed in production environment")
    except Exception as e:
        logger.error(f"Failed to run database migrations: {e}", exc_info=True)
        if settings.is_prod:
            raise
        logger.warning("Continuing startup despite migration error (non-production environment)")