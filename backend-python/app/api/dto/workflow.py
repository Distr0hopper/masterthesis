import uuid
from datetime import datetime
from enum import StrEnum

from fastapi import UploadFile
from pydantic import Field, field_validator

from app.api.dto.base import CamelModel
from app.api.dto.component import ComponentCreatorDto
from app.api.dto.pagination import PaginatedResponseDtoV1
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
        # de-duplicate while preserving order - the DB layer would reject exact dupes via
        # the composite PK anyway, but failing fast here gives a clearer 422 instead of a
        # 500 from a constraint violation
        seen: set[str] = set()
        return [d for d in value if not (d in seen or seen.add(d))]


class EmptyWorkflowDescriptionToNoneMixin:
    # same blank-Swagger/form-field issue as Component's EmptyDescriptionToNoneMixin
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
    status: WorkflowStatus
    source: WorkflowSource
    #: set only for source=workflow_builder, and cleared if that draft is deleted
    draft_id: uuid.UUID | None
    created_at: datetime


class MyWorkflowsResponseDtoV1(CamelModel):
    published: PaginatedResponseDtoV1[WorkflowListItemDto]
    pending: PaginatedResponseDtoV1[WorkflowListItemDto]


class WorkflowDetailDto(CamelModel, LinkModel):
    id: uuid.UUID
    name: str
    description: str | None
    domains: list[str]
    created_by: ComponentCreatorDto | None
    steps: list[WorkflowStepDto]
    status: WorkflowStatus
    source: WorkflowSource
    #: set only for source=workflow_builder, and cleared if that draft is deleted
    draft_id: uuid.UUID | None
    cwl_content: str
    created_at: datetime
    updated_at: datetime


class CreateWorkflowRequestDto(WorkflowDomainsValidatorMixin, EmptyWorkflowDescriptionToNoneMixin, CamelModel):
    name: str
    domains: list[str] = Field(json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    zip_file: UploadFile
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


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
    #: from label: or doc: on the uploaded document, if present
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
    PUBLISH = "PUBLISH"
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
