import uuid
from datetime import datetime

from app.api.dto.base import CamelModel


class UserResponseDto(CamelModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None
    affiliation: str | None
    created_at: datetime
