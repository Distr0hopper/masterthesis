import uuid
from datetime import datetime
from enum import StrEnum

from fastapi import UploadFile
from pydantic import Field, Json, field_validator, model_validator

from app.api.dto.base import CamelModel
from app.api.dto.component import ComponentCreatorDto, ComponentPreviewDto, FormatLabelDto
from app.api.link.model import LinkModel
from app.domain.models.component import ComponentStatus
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
    domains: list[str]
    status: ComponentStatus
    can_publish: bool


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
    """The user's decision for one previewed step, keyed by WorkflowStepPreviewDto.step_id.

    Exactly one branch: reuse_component_id binds the step to an existing catalogue
    Component, or name+domain create a new one from that step's CWL.
    """

    step_id: str
    reuse_component_id: uuid.UUID | None = None
    name: str | None = None
    domains: list[str] | None = Field(default=None, json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    #: create branch only - hand-written labels for File ports without an ontology format
    format_labels: list[FormatLabelDto] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_exactly_one_branch(self) -> "ComponentConfigDto":
        if self.reuse_component_id is not None:
            if self.name or self.domains:
                raise ValueError(f"step '{self.step_id}': reuseComponentId cannot be combined with name/domains")
            return self
        if not self.name:
            raise ValueError(f"step '{self.step_id}': either reuseComponentId or a name is required")
        if not self.domains:
            raise ValueError(f"step '{self.step_id}': at least one domain is required to create a new component")
        invalid = [d for d in self.domains if d not in VALID_DOMAINS]
        if invalid:
            raise ValueError(f"step '{self.step_id}': domains must each be one of {VALID_DOMAINS}, got: {invalid}")
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


class ExistingWorkflowDto(CamelModel):
    """The workflow currently holding a name, returned when that name is in use."""

    id: uuid.UUID
    name: str
    created_at: datetime


class WorkflowNameAvailabilityDto(CamelModel):

    name: str
    available: bool
    existing: ExistingWorkflowDto | None


class ParseWorkflowRequestDto(CamelModel):
    # may be a bare .cwl file or a .zip archive - the endpoint detects which
    file: UploadFile


class ComponentMatchDto(CamelModel):
    """An existing component a step could bind to instead of creating a new one."""

    component_id: uuid.UUID
    name: str
    version: int
    domains: list[str]
    #: fuzzy-match confidence; null for an exact name collision, which isn't a guess
    score: float | None


class WorkflowStepPreviewDto(ComponentPreviewDto):
    """One workflow step rendered as the Component it would become, so the user can review
    and configure it before the workflow is saved."""

    step_id: str
    #: "inline" (an inline CommandLineTool) or "archive" (a .cwl file from the uploaded zip)
    origin: str
    #: the `run:` filename, archive origin only
    run_reference: str | None
    suggested_name: str
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
    #: inline_only_steps or missing_external_refs have no preview.
    component_previews: list[WorkflowStepPreviewDto]
    #: steps whose run: is a plain filename, e.g. "thindata-bytime.cwl"
    external_refs: list[str]
    #: steps whose run: is an inline mapping but not class: CommandLineTool (e.g. an inline
    #: ExpressionTool or sub-Workflow). They stay embedded in the saved pipeline and never
    #: become Components, so they need no configuration - informational, not blocking.
    inline_only_steps: list[str]
    #: external_refs not found among the zip's own .cwl files - always [] for a bare
    #: .cwl upload, since there's nothing to cross-check against
    missing_external_refs: list[str]
    #: $import/$include targets resolved from the archive - preserved with the workflow and
    #: written back into every download
    auxiliary_files: list[str]
    #: referenced but absent from the archive - blocks the save, like missing_external_refs
    missing_imports: list[str]


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
    #: only read by PUBLISH - publish the workflow's still-draft components along with it.
    #: Without it, publishing a workflow that uses draft components is refused rather than
    #: silently making those components public.
    publish_components: bool = Field(
        default=False,
        description="PUBLISH only: also publish the workflow's draft components",
    )
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
