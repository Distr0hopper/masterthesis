import uuid
from datetime import datetime
from enum import StrEnum

from fastapi import UploadFile
from pydantic import Field, Json, field_validator

from app.api.dto.base import CamelModel
from app.api.dto.component import ComponentCreatorDto
from app.api.link.model import LinkModel
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.workflow import MAX_DESCRIPTION_LENGTH, WorkflowSource, WorkflowStatus
from app.domain.models.workflow_step import StepMatchStatus


class WorkflowDomainsValidatorMixin:
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


class ComponentDomainValidatorMixin:
    @field_validator("component_domain")
    @classmethod
    def validate_component_domain(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_DOMAINS:
            raise ValueError(f"component_domain must be one of {VALID_DOMAINS}, got: {value}")
        return value


class EmptyWorkflowDescriptionToNoneMixin:
    @field_validator("description", mode="before")
    @classmethod
    def empty_description_to_none(cls, value: str | None) -> str | None:
        return None if value == "" else value


class ComponentSummaryDto(CamelModel):
    id: uuid.UUID
    name: str
    version: int
    domain: str


class WorkflowStepDto(CamelModel, LinkModel):
    id: uuid.UUID
    step_id: str
    run_reference: str
    step_order: int
    component: ComponentSummaryDto | None
    match_status: StepMatchStatus
    match_score: float | None


class WorkflowListItemDto(CamelModel, LinkModel):
    id: uuid.UUID
    name: str
    description: str | None
    domains: list[str]
    step_count: int
    is_favorite: bool
    status: WorkflowStatus
    source: WorkflowSource
    #: set only for source=workflow_builder, and cleared if that draft is deleted
    draft_id: uuid.UUID | None
    created_at: datetime


class WorkflowDetailDto(CamelModel, LinkModel):
    id: uuid.UUID
    name: str
    description: str | None
    domains: list[str]
    created_by: ComponentCreatorDto | None
    steps: list[WorkflowStepDto]
    is_favorite: bool
    status: WorkflowStatus
    source: WorkflowSource
    #: set only for source=workflow_builder, and cleared if that draft is deleted
    draft_id: uuid.UUID | None
    cwl_content: str
    created_at: datetime
    updated_at: datetime


class ComponentOverrideDto(CamelModel):
    """One user-edited extracted-component name, keyed by ExtractedComponentDto.step_id."""

    step_id: str
    name: str


class CreateWorkflowRequestDto(
    WorkflowDomainsValidatorMixin, ComponentDomainValidatorMixin, EmptyWorkflowDescriptionToNoneMixin, CamelModel
):
    name: str
    domains: list[str] = Field(json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    # may be a bare .cwl file or a .zip archive - the endpoint detects which
    file: UploadFile
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    #: domain for every extracted inline component in this upload (Component.domain is a
    #: single value, distinct from Workflow.domains above) - required only if the upload
    #: actually has inline steps to extract, enforced by the service, not here
    component_domain: str | None = None
    #: user-edited names for extracted components, keyed by step_id - falls back to each
    #: component's suggested_name when omitted. One multipart form field carrying a
    #: JSON-encoded array.
    component_overrides: Json[list[ComponentOverrideDto]] = Field(default_factory=list)


class ParseWorkflowRequestDto(CamelModel):
    # may be a bare .cwl file or a .zip archive - the endpoint detects which
    file: UploadFile


class ExtractedComponentDto(CamelModel):
    """One inline CommandLineTool found in a self-contained workflow - preview only."""

    step_id: str
    suggested_name: str
    cwl_content: str
    description: str | None
    input_count: int
    output_count: int


class ParseWorkflowResponseDto(CamelModel):
    #: whether the upload was a .zip archive (vs a bare .cwl file)
    is_zip: bool
    is_self_contained: bool
    #: from label: on the uploaded document  falling back to the filename of the uploaded file -
    #: minus its .cwl extension - or, for a zip, the file that actually contains class: Workflow
    workflow_name: str | None
    step_count: int
    extracted_components: list[ExtractedComponentDto]
    #: steps whose run: is a plain filename, e.g. "thindata-bytime.cwl" - the caller must
    #: still supply these separately, this endpoint only extracts inline tools
    external_refs: list[str]
    #: steps whose run: is an inline mapping but not class: CommandLineTool (e.g. an inline
    #: ExpressionTool or sub-Workflow) - counted in step_count but not otherwise handled yet
    unsupported_inline_steps: list[str]
    #: external_refs not found among the zip's own .cwl files - always [] for a bare
    #: .cwl upload, since there's nothing to cross-check against
    missing_external_refs: list[str]


class UpdateWorkflowStepRequestDto(CamelModel):
    # explicit null clears the match back to unmatched
    component_id: uuid.UUID | None


class WorkflowCommandTypesApiV1(StrEnum):
    ADD_FAVORITE = "ADD_FAVORITE"
    REMOVE_FAVORITE = "REMOVE_FAVORITE"
    PUBLISH = "PUBLISH"
    UNPUBLISH = "UNPUBLISH"
    UPDATE_DESCRIPTION = "UPDATE_DESCRIPTION"


class WorkflowCommandExecuteRequestDto(EmptyWorkflowDescriptionToNoneMixin, CamelModel):
    command: WorkflowCommandTypesApiV1 = Field(..., description="The specific action to perform on the workflow")
    note: str | None = Field(default=None, description="Optional note for the command execution")
    # only read by UPDATE_DESCRIPTION - the new description to store (blank/omitted clears it)
    description: str | None = Field(
        default=None,
        max_length=MAX_DESCRIPTION_LENGTH,
        description="New description; only used by the UPDATE_DESCRIPTION command",
    )


class WorkflowStepCommandTypesApiV1(StrEnum):
    CONFIRM = "CONFIRM"


class WorkflowStepCommandExecuteRequestDto(CamelModel):
    command: WorkflowStepCommandTypesApiV1 = Field(..., description="The specific action to perform on the step")
    note: str | None = Field(default=None, description="Optional note for the command execution")
