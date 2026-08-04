from app.api.dto.base import CamelModel


class ErrorResponse(CamelModel):
    detail: str