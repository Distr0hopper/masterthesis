import uuid
from datetime import datetime
from enum import StrEnum
from urllib.parse import urlparse

from fastapi import UploadFile
from pydantic import Field, Json, field_validator

from app.api.dto.base import CamelModel
from app.api.link.model import LinkModel
from app.domain.compatibility.format_label import FormatLabelSource
from app.domain.compatibility.port_check import ConnectionStatus
from app.domain.models.component import MAX_DESCRIPTION_LENGTH, ComponentSource, ComponentStatus
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.parameter import ParameterDirection


class DomainsValidatorMixin:
    """Shared by DTOs where `domains` is required - Update has its own (domains is optional there)."""

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("at least one domain is required")
        invalid = [d for d in value if d not in VALID_DOMAINS]
        if invalid:
            raise ValueError(f"domains must each be one of {VALID_DOMAINS}, got invalid: {invalid}")
        seen: set[str] = set()
        return [d for d in value if not (d in seen or seen.add(d))]


class RepoUrlValidatorMixin:
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


MAX_FORMAT_LABEL_LENGTH = 64


class FormatLabelDto(CamelModel):
    """A hand-written label for a File port without an ontology format, e.g. "RDS"."""

    name: str
    direction: ParameterDirection
    #: null or blank clears the label
    label: str | None = Field(default=None, max_length=MAX_FORMAT_LABEL_LENGTH)


class ParameterDto(CamelModel):
    id: uuid.UUID
    name: str
    cwl_type: str
    default_value: str | None
    description: str | None
    format: str | None
    format_label: str | None
    # the owning component's ontology (Component.ontology_url), repeated per port so the
    # builder can tell from a port alone whether two formats are comparable
    ontology_url: str | None
    #: where format_label came from - null when there is neither label nor ontology format
    format_label_source: FormatLabelSource | None
    #: whether a hand-written label may be set on this port (UPDATE_FORMAT_LABELS, upload)
    accepts_manual_format_label: bool
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
    domains: list[str]
    status: ComponentStatus
    created_at: datetime
    is_favorite: bool
    # opt-in only (`?includeParameters=true`), hence None rather than []: browse/home/mine
    # never read it and shouldn't pay for it, while the workflow builder needs the ports of
    # every listed component at once to rank its palette. Costs no extra query - the
    # relationship is already lazy="selectin", so these rows are loaded either way.
    parameters: list[ParameterDto] | None = None
    # only present when the request passed `rankAgainst` - how this component fits the
    # builder canvas it was ranked against (null: nothing on the canvas fits it)
    match: "ComponentMatchDto | None" = None


class ComponentMatchDto(CamelModel):
    """A palette candidate's best fit on the canvas."""

    #: higher ranks first; negative when the component has no data inputs at all
    score: int
    #: compatible (format-checked) or unverified (the types fit, the formats are unknown)
    status: ConnectionStatus | None
    #: the canvas component whose outputs it fits - null when nothing matched
    component_id: uuid.UUID | None
    component_name: str | None


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
    ontology_url: str | None
    domains: list[str]
    source: ComponentSource
    status: ComponentStatus
    parameters: list[ParameterDto]
    created_at: datetime
    updated_at: datetime
    is_favorite: bool


class PreviewParameterDto(CamelModel):
    """A previewed component port. Deliberately NOT ParameterDto: that carries a real
    uuid primary key, and these are never persisted - the id here is a synthetic,
    stable-within-one-response string that only exists to give the UI a list key."""

    id: str
    name: str
    cwl_type: str
    default_value: str | None
    description: str | None
    format: str | None
    format_label: str | None
    # the owning component's ontology (Component.ontology_url), repeated per port so the
    # builder can tell from a port alone whether two formats are comparable
    ontology_url: str | None
    #: where format_label came from - null when there is neither label nor ontology format
    format_label_source: FormatLabelSource | None
    #: whether a hand-written label may be set on this port (UPDATE_FORMAT_LABELS, upload)
    accepts_manual_format_label: bool
    direction: ParameterDirection


class ComponentPreviewDto(CamelModel):
    """Everything read out of a CWL document without persisting it.

    Shared by both upload flows: /components/parse returns exactly this, and the workflow
    upload's per-step ComponentPreviewDto extends it with the step it came from.
    """

    description: str | None
    cwl_content: str
    cwl_type: str | None
    dockerfile_content: str | None
    docker_pull_reference: str | None
    ontology_url: str | None
    parameters: list[PreviewParameterDto]


class ParseComponentRequestDto(CamelModel):
    cwl_file: UploadFile


class ExistingComponentDto(CamelModel):
    """The component currently holding a name, returned when that name is taken."""

    id: uuid.UUID
    name: str
    version: int
    domains: list[str]
    status: ComponentStatus
    can_add_version: bool


class NameAvailabilityDto(CamelModel):
    """Whether a component name can still be claimed. Lets a caller warn (and offer to
    reuse the existing component) while the user is typing, instead of only failing with
    a 409 after the whole upload has been submitted."""

    name: str
    available: bool
    #: the latest version of the lineage already holding this name, if any
    existing: ExistingComponentDto | None


class CreateComponentRequestDto(
    DomainsValidatorMixin, RepoUrlValidatorMixin, EmptyRepoCommitShaToNoneMixin, EmptyDescriptionToNoneMixin, CamelModel
):
    name: str
    # json_schema_extra adds the enum purely so Swagger UI renders a dropdown -
    # the actual type stays plain str, validated for real by DomainsValidatorMixin.
    # Repeated multipart field, exactly like CreateWorkflowRequestDto.domains.
    domains: list[str] = Field(json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    cwl_file: UploadFile
    author_name: str | None = None
    repo_url: str | None = None
    repo_commit_sha: str | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    #: hand-written labels for File ports without an ontology format - one multipart form
    #: field carrying a JSON-encoded array, like CreateWorkflowRequestDto.component_configs
    format_labels: Json[list[FormatLabelDto]] = Field(default_factory=list)

    @field_validator("repo_url", mode="before")
    @classmethod
    def empty_repo_url_to_none(cls, value: str | None) -> str | None:
        return None if value == "" else value


class AddVersionRequestDto(EmptyRepoCommitShaToNoneMixin, EmptyDescriptionToNoneMixin, CamelModel):
    cwl_file: UploadFile
    repo_commit_sha: str | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


class PackageComponentRequestDto(DomainsValidatorMixin, RepoUrlValidatorMixin, CamelModel):
    repo_url: str
    domains: list[str] = Field(json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


class ComponentCommandTypesApiV1(StrEnum):
    ADD_FAVORITE = "ADD_FAVORITE"
    REMOVE_FAVORITE = "REMOVE_FAVORITE"
    REPACKAGE = "REPACKAGE"
    PUBLISH = "PUBLISH"
    UNPUBLISH = "UNPUBLISH"
    UPDATE_DESCRIPTION = "UPDATE_DESCRIPTION"
    UPDATE_DOMAIN = "UPDATE_DOMAIN"
    UPDATE_FORMAT_LABELS = "UPDATE_FORMAT_LABELS"


class ComponentCommandExecuteRequestDto(EmptyDescriptionToNoneMixin, CamelModel):
    command: ComponentCommandTypesApiV1 = Field(..., description="The specific action to perform on the component")
    note: str | None = Field(default=None, description="Optional note for the command execution")
    description: str | None = Field(
        default=None,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="New description; only used by the UPDATE_DESCRIPTION command",
    )
    domains: list[str] | None = Field(
        default=None,
        json_schema_extra={"items": {"enum": VALID_DOMAINS}},
        description="New domains; only used by the UPDATE_DOMAIN command",
    )
    format_labels: list[FormatLabelDto] | None = Field(
        default=None,
        description="Hand-written labels for File ports without an ontology format; only used by the "
        "UPDATE_FORMAT_LABELS command",
    )

    @field_validator("domains")
    @classmethod
    def validate_domains(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if not value:
            raise ValueError("at least one domain is required")
        invalid = [d for d in value if d not in VALID_DOMAINS]
        if invalid:
            raise ValueError(f"domains must each be one of {VALID_DOMAINS}, got invalid: {invalid}")
        seen: set[str] = set()
        return [d for d in value if not (d in seen or seen.add(d))]