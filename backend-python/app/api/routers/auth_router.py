from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dto.auth import AuthResponseDto, RequestOtpDto, RequestOtpResponseDto, VerifyOtpDto
from app.api.dto.common import ErrorResponse
from app.application.service.auth_service import AuthService
from app.application.service.otp_service import OtpService
from app.domain.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/otp/request",
    response_model=RequestOtpResponseDto,
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Too many requests"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def request_otp(
    dto: RequestOtpDto,
    otp_service: Annotated[OtpService, Depends(OtpService.get_service)],
) -> RequestOtpResponseDto:
    cooldown_seconds = await otp_service.request_code(dto.email)
    return RequestOtpResponseDto(cooldown_seconds=cooldown_seconds)


@router.post(
    "/otp/verify",
    response_model=AuthResponseDto,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Invalid, expired, or exhausted code"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def verify_otp(
    dto: VerifyOtpDto,
    otp_service: Annotated[OtpService, Depends(OtpService.get_service)],
) -> AuthResponseDto:
    access_token, expires_in = await otp_service.verify_code(dto.email, dto.code)
    return AuthResponseDto(access_token=access_token, expires_in=expires_in)


@router.post(
    "/refresh",
    response_model=AuthResponseDto,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing, invalid or expired token"},
    },
)
async def refresh(
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    auth_service: Annotated[AuthService, Depends(AuthService.get_service)],
) -> AuthResponseDto:
    """A fresh token for a still-valid one - the frontend's sliding session. It calls this
    while the user is active, so a session only ends after a full token lifetime
    (JWT_EXPIRES_IN) without any activity. An already expired token can't be refreshed."""
    access_token, expires_in = auth_service.issue_token(current_user)
    return AuthResponseDto(access_token=access_token, expires_in=expires_in)
