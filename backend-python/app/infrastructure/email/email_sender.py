from abc import ABC, abstractmethod

from app.config import get_settings


class EmailSender(ABC):
    @abstractmethod
    async def send_otp_email(self, to: str, code: str) -> None: ...

    @staticmethod
    def get_sender() -> "EmailSender":
        settings = get_settings()
        if settings.email_provider == "resend":
            from app.infrastructure.email.resend_email_sender import ResendEmailSender

            return ResendEmailSender()

        from app.infrastructure.email.smtp_email_sender import SmtpEmailSender

        return SmtpEmailSender()