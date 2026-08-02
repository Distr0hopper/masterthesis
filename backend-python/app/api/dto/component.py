import uuid
from datetime import datetime

from app.api.dto.base import CamelModel
from app.domain.models.component import ComponentSource
from app.domain.models.parameter import ParameterDirection


class ParameterDto(CamelModel):
    id: uuid.UUID
    name: str
    cwl_type: str
    default_value: str | None
    description: str | None
    direction: ParameterDirection


class ComponentCreatorDto(CamelModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None


class ComponentListItemDto(CamelModel):
    id: uuid.UUID
    name: str
    author_name: str | None
    repo_url: str | None
    repo_commit_sha: str | None
    version: int
    domain: str
    source: ComponentSource
    created_at: datetime


class ComponentDetailDto(CamelModel):
    id: uuid.UUID
    name: str
    author_name: str | None
    created_by: ComponentCreatorDto | None
    description: str | None
    repo_url: str | None
    repo_commit_sha: str | None
    doi: str | None
    version: int
    cwl_content: str
    domain: str
    source: ComponentSource
    parameters: list[ParameterDto]
    created_at: datetime