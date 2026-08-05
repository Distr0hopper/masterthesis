from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.dto.common import ErrorResponse
from app.api.dto.user import UpdateUserRequestDto, UserResponseDto
from app.api.transformer.user_transformer import UserTransformer
from app.application.service.auth_service import AuthService
from app.application.service.users_service import UsersService
from app.domain.models.user import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponseDto,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"}},
)
async def me(current_user: Annotated[User, Depends(AuthService.get_current_user)]) -> UserResponseDto:
    return UserTransformer.to_user_response(current_user)


@router.patch(
    "/me",
    response_model=UserResponseDto,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def update_me(
    dto: UpdateUserRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    users_service: Annotated[UsersService, Depends(UsersService.get_service)],
) -> UserResponseDto:
    updated = UserTransformer.apply_update_dto(current_user, dto)
    saved = await users_service.update_user(updated)
    return UserTransformer.to_user_response(saved)