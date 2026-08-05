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


class UpdateUserRequestDto(CamelModel):
    # all fields omitted -> unchanged; presence-tracked via model_fields_set so an
    # explicit null clears the field, distinct from the field being left out entirely
    first_name: str | None = None
    last_name: str | None = None
    affiliation: str | None = None
