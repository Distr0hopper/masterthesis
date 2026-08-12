from app.api.dto.base import CamelModel


class DomainDto(CamelModel):
    id: str
    color: str
