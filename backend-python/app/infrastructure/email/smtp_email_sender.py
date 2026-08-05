from email.message import EmailMessage

import aiosmtplib

from app.config import get_settings
from app.infrastructure.email.email_sender import EmailSender

settings = get_settings()


class SmtpEmailSender(EmailSender):
    async def send_otp_email(self, to: str, code: str) -> None:
        message = EmailMessage()
        message["From"] = settings.smtp_from_email
        message["To"] = to
        message["Subject"] = "Your login code"
        message.set_content(f"Your login code is {code}. It expires in {settings.otp_expires_in // 60} minutes.")

        await aiosmtplib.send(message, hostname=settings.smtp_host, port=settings.smtp_port)