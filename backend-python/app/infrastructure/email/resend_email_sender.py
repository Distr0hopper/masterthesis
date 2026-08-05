import resend

from app.config import get_settings
from app.infrastructure.email.email_sender import EmailSender

settings = get_settings()


class ResendEmailSender(EmailSender):
    async def send_otp_email(self, to: str, code: str) -> None:
        resend.api_key = settings.resend_api_key
        await resend.Emails.send_async(
            {
                "from": settings.resend_from_email,
                "to": [to],
                "subject": "Your login code",
                "text": f"Your login code is {code}. It expires in {settings.otp_expires_in // 60} minutes.",
            }
        )