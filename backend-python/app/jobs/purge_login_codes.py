"""Delete expired login codes - see LoginCodeRetentionService.

Run on a schedule from the backend image: `python -m app.jobs.purge_login_codes`. Locally
the `login-code-purge` service in the root docker-compose.yml runs it every hour; on a
platform like Kubernetes it would be a CronJob. Exits 0 on success and 1 on failure, so the
scheduler can see and retry a failed run.
"""

import asyncio
import logging
import sys

from app.application.service.login_code_retention_service import LoginCodeRetentionService
from app.infrastructure.db.session import async_session_factory, engine
from app.infrastructure.db.unit_of_work import SqlUnitOfWork

logger = logging.getLogger("app.jobs.purge_login_codes")


async def run() -> int:
    try:
        async with async_session_factory() as session:
            deleted = await LoginCodeRetentionService(SqlUnitOfWork(session)).purge_expired()
    finally:
        await engine.dispose()
    logger.info(f"Deleted {deleted} expired login code(s)")
    return deleted


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        asyncio.run(run())
    except Exception:
        logger.exception("Purging expired login codes failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
