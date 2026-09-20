import uuid
from datetime import datetime
from enum import StrEnum

from fastapi import UploadFile
from pydantic import Field, Json, field_validator, model_validator

from app.api.dto.base import CamelModel
from app.api.dto.component import ComponentCreatorDto
from app.domain.models.parameter import ParameterDirection
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


class ComponentConfigDto(CamelModel):
    """The user's decision for one previewed step, keyed by ComponentPreviewDto.step_id.

    Exactly one branch: reuse_component_id binds the step to an existing catalogue
    Component, or name+domain create a new one from that step's CWL.
    """

    step_id: str
    reuse_component_id: uuid.UUID | None = None
    name: str | None = None
    domain: str | None = Field(default=None, json_schema_extra={"enum": VALID_DOMAINS})
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)

    @model_validator(mode="after")
    def validate_exactly_one_branch(self) -> "ComponentConfigDto":
        if self.reuse_component_id is not None:
            if self.name or self.domain:
                raise ValueError(f"step '{self.step_id}': reuseComponentId cannot be combined with name/domain")
            return self
        if not self.name:
            raise ValueError(f"step '{self.step_id}': either reuseComponentId or a name is required")
        if not self.domain:
            raise ValueError(f"step '{self.step_id}': domain is required when creating a new component")
        if self.domain not in VALID_DOMAINS:
            raise ValueError(f"step '{self.step_id}': domain must be one of {VALID_DOMAINS}, got: {self.domain}")
        return self


class CreateWorkflowRequestDto(WorkflowDomainsValidatorMixin, EmptyWorkflowDescriptionToNoneMixin, CamelModel):
    name: str
    domains: list[str] = Field(json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    # may be a bare .cwl file or a .zip archive - the endpoint detects which
    file: UploadFile
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    #: one entry per workflow step - every step must be configured before the workflow can
    #: be created (the service rejects any that isn't). One multipart form field carrying
    #: a JSON-encoded array.
    component_configs: Json[list[ComponentConfigDto]] = Field(default_factory=list)


class ParseWorkflowRequestDto(CamelModel):
    # may be a bare .cwl file or a .zip archive - the endpoint detects which
    file: UploadFile


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
    direction: ParameterDirection


class ComponentMatchDto(CamelModel):
    """An existing component a step could bind to instead of creating a new one."""

    component_id: uuid.UUID
    name: str
    version: int
    domain: str
    #: fuzzy-match confidence; null for an exact name collision, which isn't a guess
    score: float | None


class ComponentPreviewDto(CamelModel):
    """One workflow step rendered as the Component it would become, so the user can review
    and configure it before the workflow is saved."""

    step_id: str
    #: "inline" (an inline CommandLineTool) or "archive" (a .cwl file from the uploaded zip)
    origin: str
    #: the `run:` filename, archive origin only
    run_reference: str | None
    suggested_name: str
    description: str | None
    cwl_content: str
    cwl_type: str | None
    dockerfile_content: str | None
    docker_pull_reference: str | None
    parameters: list[PreviewParameterDto]
    #: an existing component that already holds suggested_name - the user must rename or reuse
    name_conflict: ComponentMatchDto | None
    #: archive origin only - the catalogue component this step's run: filename matches
    suggested_match: ComponentMatchDto | None


class ParseWorkflowResponseDto(CamelModel):
    #: whether the upload was a .zip archive (vs a bare .cwl file)
    is_zip: bool
    is_self_contained: bool
    #: from label: on the uploaded document  falling back to the filename of the uploaded file -
    #: minus its .cwl extension - or, for a zip, the file that actually contains class: Workflow
    workflow_name: str | None
    step_count: int
    #: one per resolvable step, inline and archive alike. Steps listed in
    #: unsupported_inline_steps or missing_external_refs have no preview.
    component_previews: list[ComponentPreviewDto]
    #: steps whose run: is a plain filename, e.g. "thindata-bytime.cwl"
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
