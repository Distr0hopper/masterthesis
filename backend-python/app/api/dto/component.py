import uuid
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse

from fastapi import UploadFile
from pydantic import Field, field_validator

from app.api.dto.base import CamelModel
from app.api.link.model import LinkModel
from app.domain.models.component import MAX_DESCRIPTION_LENGTH, ComponentSource, ComponentStatus
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


class EmptyDescriptionToNoneMixin:
    # same blank-Swagger/form-field issue as above - an empty description must fall back
    # to the CWL's own `doc:` field (see ComponentsService.create_manual /
    # add_manual_version, which only auto-extract when description is None), not get
    # stored as "" verbatim
    @field_validator("description", mode="before")
    @classmethod
    def empty_description_to_none(cls, value: str | None) -> str | None:
        return None if value == "" else value


class ParameterDto(CamelModel):
    id: uuid.UUID
    name: str
    cwl_type: str
    default_value: str | None
    description: str | None
    format: str | None
    format_label: str | None
    direction: ParameterDirection


class ComponentCreatorDto(CamelModel):
    id: uuid.UUID
    email: str
    first_name: str | None
    last_name: str | None


class ComponentListItemDto(CamelModel, LinkModel):
    id: uuid.UUID
    name: str
    description: str | None
    author_name: str | None
    repo_url: str | None
    version: int
    domain: str
    status: ComponentStatus
    created_at: datetime
    is_favorite: bool
    # opt-in only (`?includeParameters=true`), hence None rather than []: browse/home/mine
    # never read it and shouldn't pay for it, while the workflow builder needs the ports of
    # every listed component at once to rank its palette. Costs no extra query - the
    # relationship is already lazy="selectin", so these rows are loaded either way.
    parameters: list[ParameterDto] | None = None


class ComponentDetailDto(CamelModel, LinkModel):
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
    cwl_type: str | None
    dockerfile_content: str | None
    docker_pull_reference: str | None
    domain: str
    source: ComponentSource
    status: ComponentStatus
    parameters: list[ParameterDto]
    created_at: datetime
    updated_at: datetime
    is_favorite: bool


class CreateComponentRequestDto(
    DomainValidatorMixin, RepoUrlValidatorMixin, EmptyRepoCommitShaToNoneMixin, EmptyDescriptionToNoneMixin, CamelModel
):
    name: str
    # json_schema_extra adds the enum purely so Swagger UI renders a dropdown -
    # the actual type stays plain str, validated for real by DomainValidatorMixin
    domain: str = Field(json_schema_extra={"enum": VALID_DOMAINS})
    cwl_file: UploadFile
    author_name: str | None = None
    repo_url: str | None = None
    repo_commit_sha: str | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    @field_validator("repo_url", mode="before")
    @classmethod
    def empty_repo_url_to_none(cls, value: str | None) -> str | None:
        return None if value == "" else value


class AddVersionRequestDto(EmptyRepoCommitShaToNoneMixin, EmptyDescriptionToNoneMixin, CamelModel):
    cwl_file: UploadFile
    repo_commit_sha: str | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


class UpdateComponentRequestDto(CamelModel):
    # domain omitted -> None -> "no change" (Component.domain can never be cleared to null,
    # so None is unambiguous here - unlike description below, no presence-tracking needed).
    # Domain is optional here (unlike Create/Package), so this can't reuse DomainValidatorMixin.
    domain: str | None = Field(default=None, json_schema_extra={"enum": VALID_DOMAINS})
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_DOMAINS:
            raise ValueError(f"domain must be one of {VALID_DOMAINS}")
        return value


class PackageComponentRequestDto(DomainValidatorMixin, RepoUrlValidatorMixin, CamelModel):
    repo_url: str
    domain: str = Field(json_schema_extra={"enum": VALID_DOMAINS})
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


class ComponentCommandTypesApiV1(StrEnum):
    ADD_FAVORITE = "ADD_FAVORITE"
    REMOVE_FAVORITE = "REMOVE_FAVORITE"
    REPACKAGE = "REPACKAGE"
    PUBLISH = "PUBLISH"


class ComponentCommandExecuteRequestDto(CamelModel):
    command: ComponentCommandTypesApiV1 = Field(..., description="The specific action to perform on the component")
    note: str | None = Field(default=None, description="Optional note for the command execution")