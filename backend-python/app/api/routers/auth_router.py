from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dto.auth import AuthResponseDto, RequestOtpDto, VerifyOtpDto
from app.api.dto.common import ErrorResponse
from app.application.service.otp_service import OtpService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/otp/request",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_429_TOO_MANY_REQUESTS: {"model": ErrorResponse, "description": "Too many requests"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def request_otp(
    dto: RequestOtpDto,
    otp_service: Annotated[OtpService, Depends(OtpService.get_service)],
) -> None:
    await otp_service.request_code(dto.email)


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