from fastapi import APIRouter, Depends, status

from app.api.dto.auth import AuthResponseDto, LoginRequestDto, RegisterRequestDto
from app.api.dto.user import UserResponseDto
from app.api.transformer.user_transformer import to_user_response
from app.application.service.auth_service import AuthService
from app.domain.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponseDto, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequestDto, auth_service: AuthService = Depends(AuthService.get_service)) -> UserResponseDto:
    user = await auth_service.register(request.email, request.first_name, request.last_name, request.password)
    return to_user_response(user)


@router.post("/login", response_model=AuthResponseDto)
async def login(request: LoginRequestDto, auth_service: AuthService = Depends(AuthService.get_service)) -> AuthResponseDto:
    user = await auth_service.validate_user(request.email, request.password)
    access_token, expires_in = auth_service.issue_token(user)
    return AuthResponseDto(access_token=access_token, expires_in=expires_in)


@router.get("/me", response_model=UserResponseDto)
async def me(current_user: User = Depends(AuthService.get_current_user)) -> UserResponseDto:
    return to_user_response(current_user)
