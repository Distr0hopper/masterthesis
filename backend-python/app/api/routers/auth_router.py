from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dto.auth import AuthResponseDto, LoginRequestDto, RegisterRequestDto
from app.api.dto.common import ErrorResponse
from app.api.dto.user import UserResponseDto
from app.api.transformer.user_transformer import UserTransformer
from app.application.service.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponseDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "Email already registered"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def register(
    dto: RegisterRequestDto,
    auth_service: Annotated[AuthService, Depends(AuthService.get_service)],
) -> UserResponseDto:
    user = await auth_service.register(dto.email, dto.first_name, dto.last_name, dto.password)
    return UserTransformer.to_user_response(user)


@router.post(
    "/login",
    response_model=AuthResponseDto,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Invalid email or password"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def login(
    dto: LoginRequestDto,
    auth_service: Annotated[AuthService, Depends(AuthService.get_service)],
) -> AuthResponseDto:
    user = await auth_service.validate_user(dto.email, dto.password)
    access_token, expires_in = auth_service.issue_token(user)
    return AuthResponseDto(access_token=access_token, expires_in=expires_in)
