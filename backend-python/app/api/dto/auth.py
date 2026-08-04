from pydantic import BaseModel, EmailStr, Field

from app.api.dto.base import CamelModel


class RegisterRequestDto(CamelModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str = Field(min_length=8)


class LoginRequestDto(CamelModel):
    email: EmailStr
    password: str


class AuthResponseDto(CamelModel):
    access_token: str
    expires_in: int
