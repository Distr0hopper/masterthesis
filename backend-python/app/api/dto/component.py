import uuid
from datetime import datetime
from urllib.parse import urlparse

from fastapi import UploadFile
from pydantic import Field, field_validator

from app.api.dto.base import CamelModel
from app.domain.models.component import ComponentSource
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.parameter import ParameterDirection


class DomainValidatorMixin:
    """Shared by DTOs where `domain` is required - Update has its own (domain is optional there)."""

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str) -> str:
        if value not in VALID_DOMAINS:
            raise ValueError(f"domain must be one of {VALID_DOMAINS}")
        return value


class RepoUrlValidatorMixin:
    # value: str | None works for both optional and required repo_url fields - on a
    # required field pydantic's own type validation already guarantees non-None by the
    # time this runs, so the `is not None` check is simply always-true there
    @field_validator("repo_url")
    @classmethod
    def validate_repo_url(cls, value: str | None) -> str | None:
        if value is not None:
            parsed = urlparse(value)
            if not (parsed.scheme and parsed.netloc):
                raise ValueError("repoUrl must be a valid URL")
        return value


class EmptyRepoCommitShaToNoneMixin:
    # a blank Swagger/form field arrives as "", not omitted - without this, "" (not NULL)
    # gets stored and collides with the partial unique index on (name, repo_commit_sha)
    @field_validator("repo_commit_sha", mode="before")
    @classmethod
    def empty_repo_commit_sha_to_none(cls, value: str | None) -> str | None:
        return None if value == "" else value


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


class CreateComponentRequestDto(DomainValidatorMixin, RepoUrlValidatorMixin, EmptyRepoCommitShaToNoneMixin, CamelModel):
    name: str
    # json_schema_extra adds the enum purely so Swagger UI renders a dropdown -
    # the actual type stays plain str, validated for real by DomainValidatorMixin
    domain: str = Field(json_schema_extra={"enum": VALID_DOMAINS})
    cwl_file: UploadFile
    author_name: str | None = None
    repo_url: str | None = None
    repo_commit_sha: str | None = None
    description: str | None = None

    @field_validator("repo_url", mode="before")
    @classmethod
    def empty_repo_url_to_none(cls, value: str | None) -> str | None:
        return None if value == "" else value


class AddVersionRequestDto(EmptyRepoCommitShaToNoneMixin, CamelModel):
    cwl_file: UploadFile
    repo_commit_sha: str | None = None
    description: str | None = None


class UpdateComponentRequestDto(CamelModel):
    # domain omitted -> None -> "no change" (Component.domain can never be cleared to null,
    # so None is unambiguous here - unlike description below, no presence-tracking needed).
    # Domain is optional here (unlike Create/Package), so this can't reuse DomainValidatorMixin.
    domain: str | None = Field(default=None, json_schema_extra={"enum": VALID_DOMAINS})
    description: str | None = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_DOMAINS:
            raise ValueError(f"domain must be one of {VALID_DOMAINS}")
        return value


class PackageComponentRequestDto(DomainValidatorMixin, RepoUrlValidatorMixin, CamelModel):
    repo_url: str
    domain: str = Field(json_schema_extra={"enum": VALID_DOMAINS})
    description: str | None = None