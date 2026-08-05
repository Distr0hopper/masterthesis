from app.api.dto.user import UpdateUserRequestDto, UserResponseDto
from app.domain.models.user import User


class UserTransformer:
    @staticmethod
    def to_user_response(user: User) -> UserResponseDto:
        return UserResponseDto(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            affiliation=user.affiliation,
            created_at=user.created_at,
        )

    @staticmethod
    def apply_update_dto(user: User, dto: UpdateUserRequestDto) -> User:
        fields_set = dto.model_fields_set
        if "first_name" in fields_set:
            user.first_name = dto.first_name
        if "last_name" in fields_set:
            user.last_name = dto.last_name
        if "affiliation" in fields_set:
            user.affiliation = dto.affiliation
        return user