"""DTOs only a tool - the leaf of the composite - has."""

from enum import StrEnum
from typing import Literal
from urllib.parse import urlparse

from fastapi import UploadFile
from pydantic import Field, Json, field_validator

from app.api.dto.base import CamelModel
from app.api.dto.component import (
    ComponentDetailBaseDto,
    ComponentListItemBaseDto,
    DomainsValidatorMixin,
    EmptyDescriptionToNoneMixin,
    ExistingComponentDto,
    FormatLabelDto,
    PreviewParameterDto,
)
from app.domain.models.component import MAX_DESCRIPTION_LENGTH, ComponentKind
from app.domain.models.component_domain import VALID_DOMAINS


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


class ToolListItemDto(ComponentListItemBaseDto):
    kind: Literal[ComponentKind.TOOL] = ComponentKind.TOOL
    repo_url: str | None


class ToolDetailDto(ComponentDetailBaseDto):
    kind: Literal[ComponentKind.TOOL] = ComponentKind.TOOL
    #: the CWL class - CommandLineTool or ExpressionTool
    cwl_type: str | None
    dockerfile_content: str | None
    docker_pull_reference: str | None


class ToolPreviewDto(CamelModel):
    """Everything read out of a tool's CWL document without persisting it.

    Shared by both upload flows: /tools/parse returns exactly this, and the workflow
    upload's per-step WorkflowStepPreviewDto extends it with the step it came from.
    """

    description: str | None
    cwl_content: str
    cwl_type: str | None
    dockerfile_content: str | None
    docker_pull_reference: str | None
    ontology_url: str | None
    parameters: list[PreviewParameterDto]


class ParseToolRequestDto(CamelModel):
    cwl_file: UploadFile


class CreateToolRequestDto(
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
    #: field carrying a JSON-encoded array, like CreateWorkflowRequestDto.component_configs.
    format_labels: Json[list[FormatLabelDto]] = Field(default="[]", validate_default=True)

    @field_validator("repo_url", mode="before")
    @classmethod
    def empty_repo_url_to_none(cls, value: str | None) -> str | None:
        return None if value == "" else value


class AddVersionRequestDto(EmptyRepoCommitShaToNoneMixin, EmptyDescriptionToNoneMixin, CamelModel):
    cwl_file: UploadFile
    repo_commit_sha: str | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


class PackageToolRequestDto(DomainsValidatorMixin, RepoUrlValidatorMixin, EmptyDescriptionToNoneMixin, CamelModel):
    repo_url: str
    domains: list[str] = Field(json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    #: name for a new lineage (defaults to the repo name) - ignored when the repo is
    #: already packaged, since a new version keeps its lineage's name
    name: str | None = None
    #: hand-written labels for the generated File ports, as reviewed in the preview
    format_labels: list[FormatLabelDto] = []
    #: commit the preview was generated from - packaging fails with 409 if the repo has
    #: moved on since, so nothing unreviewed gets saved
    expected_commit_sha: str | None = None


class PackagePreviewRequestDto(RepoUrlValidatorMixin, CamelModel):
    repo_url: str


class PackagePreviewDto(ToolPreviewDto):
    """A GitHub repo packaged but not persisted (POST /tools/package/preview)."""

    repo_name: str
    repo_url: str
    commit_sha: str
    author: str | None
    #: latest version of the lineage already packaged from this repo - creating then
    #: adds a new version to it instead of a new tool
    existing: ExistingComponentDto | None
    #: the repo's current commit is already packaged as `existing`
    already_packaged: bool


class ToolCommandTypesApiV1(StrEnum):
    REPACKAGE = "REPACKAGE"
    UPDATE_FORMAT_LABELS = "UPDATE_FORMAT_LABELS"


class ToolCommandExecuteRequestDto(CamelModel):
    command: ToolCommandTypesApiV1 = Field(..., description="The specific action to perform on the tool")
    note: str | None = Field(default=None, description="Optional note for the command execution")
    format_labels: list[FormatLabelDto] | None = Field(
        default=None,
        description="Hand-written labels for File ports without an ontology format; only used by the "
        "UPDATE_FORMAT_LABELS command",
    )
