"""Recreate the end-to-end tests' own database - empty, for the backend's startup migrations.

Run by frontend/playwright.config.ts before it starts the backend against that database:
`DATABASE_NAME=component_repository_e2e uv run python -m scripts.recreate_e2e_database`.
It lives next to the dev database in the Compose Postgres (`make docker-infra`), and this
refuses any other name, so the dev data can never be the one dropped.
"""

import asyncio
import sys

import asyncpg

from app.config import get_settings

E2E_DATABASE = "component_repository_e2e"


async def recreate() -> None:
    settings = get_settings()
    if settings.database_name != E2E_DATABASE:
        sys.exit(f"refusing to recreate {settings.database_name!r} - only {E2E_DATABASE!r}")
    connection = await asyncpg.connect(
        host=settings.database_host,
        port=settings.database_port,
        user=settings.database_user,
        password=settings.database_password,
        database="postgres",
    )
    try:
        await connection.execute(f'DROP DATABASE IF EXISTS "{E2E_DATABASE}" WITH (FORCE)')
        await connection.execute(f'CREATE DATABASE "{E2E_DATABASE}"')
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(recreate())
