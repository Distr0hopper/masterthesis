from pydantic import EmailStr, Field

from app.api.dto.base import CamelModel


class RequestOtpDto(CamelModel):
    email: EmailStr


class VerifyOtpDto(CamelModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class AuthResponseDto(CamelModel):
    access_token: str
    expires_in: int