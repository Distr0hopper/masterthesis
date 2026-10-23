from datetime import datetime, timezone

from app.application.unit_of_work import UnitOfWork


class LoginCodeRetentionService:
    """How long login codes are kept. A code that expired can never log anyone in again, but
    its row still holds an email address - so expired codes are deleted.

    Not part of the request path: OtpService already keeps at most one code per email
    (a new code replaces the earlier ones, a used one is deleted). What it leaves behind is
    the last code of every email that requested one and never logged in - those are
    purged on a schedule by app.jobs.purge_login_codes.
    """

    def __init__(self, uow: UnitOfWork):
        self.uow = uow

    async def purge_expired(self) -> int:
        """Delete every expired code; returns how many. Idempotent - running it twice, or
        twice at once, deletes nothing extra."""
        async with self.uow:
            deleted = await self.uow.login_codes.delete_expired(datetime.now(timezone.utc))
            await self.uow.commit()
        return deleted
