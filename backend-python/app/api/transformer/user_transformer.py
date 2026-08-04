from app.api.dto.user import UserResponseDto
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