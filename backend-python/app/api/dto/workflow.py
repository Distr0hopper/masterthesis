"""DTOs only a workflow - the composite - has: its steps and its upload flow."""

import uuid
from typing import Literal

from fastapi import UploadFile
from pydantic import Field, Json, model_validator

from app.api.dto.base import CamelModel
from app.api.dto.component import (
    ComponentDetailBaseDto,
    ComponentListItemBaseDto,
    DomainsValidatorMixin,
    EmptyDescriptionToNoneMixin,
    FormatLabelDto,
)
from app.api.dto.tool import ToolPreviewDto
from app.api.link.model import LinkModel
from app.application.commands.commands import WorkflowStepCommandType
from app.domain.models.component import MAX_DESCRIPTION_LENGTH, ComponentKind, ComponentSource, ComponentStatus
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.workflow_step import StepMatchStatus


class ComponentSummaryDto(CamelModel):
    """The child a step runs - a tool, or a nested workflow."""

    id: uuid.UUID
    kind: ComponentKind
    name: str
    version: int
    domains: list[str]
    status: ComponentStatus
    #: why the child is deprecated - set only while it is
    deprecation_note: str | None = None
    can_publish: bool


class WorkflowStepDto(CamelModel, LinkModel):
    id: uuid.UUID
    step_id: str
    run_reference: str
    step_order: int
    component: ComponentSummaryDto | None
    match_status: StepMatchStatus
    match_score: float | None


class WorkflowListItemDto(ComponentListItemBaseDto):
    kind: Literal[ComponentKind.WORKFLOW] = ComponentKind.WORKFLOW
    step_count: int
    source: ComponentSource
    #: set only for source=workflow_builder, and cleared if that draft is deleted
    draft_id: uuid.UUID | None


class WorkflowDetailDto(ComponentDetailBaseDto):
    kind: Literal[ComponentKind.WORKFLOW] = ComponentKind.WORKFLOW
    steps: list[WorkflowStepDto]
    draft_id: uuid.UUID | None


class ComponentConfigDto(CamelModel):
    """The user's decision for one previewed step, keyed by WorkflowStepPreviewDto.step_id.

    Exactly one branch: reuse_component_id binds the step to an existing catalogue
    component, new_version_of_id adds the step's CWL as the next version of one of the
    caller's tools, or name+domain create a new component from it - a tool, or a nested
    workflow from the archive. A step below a nested workflow that is reused needs no entry.
    """

    step_id: str
    reuse_component_id: uuid.UUID | None = None
    #: the caller's tool the step's CWL becomes the next version of - keeps its name and domains
    new_version_of_id: uuid.UUID | None = None
    name: str | None = None
    domains: list[str] | None = Field(default=None, json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    #: create and new-version branches - hand-written labels for File ports without an ontology format
    format_labels: list[FormatLabelDto] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_exactly_one_branch(self) -> "ComponentConfigDto":
        if self.reuse_component_id is not None and self.new_version_of_id is not None:
            raise ValueError(f"step '{self.step_id}': reuseComponentId cannot be combined with newVersionOfId")
        if self.reuse_component_id is not None or self.new_version_of_id is not None:
            if self.name or self.domains:
                branch = "reuseComponentId" if self.reuse_component_id is not None else "newVersionOfId"
                raise ValueError(f"step '{self.step_id}': {branch} cannot be combined with name/domains")
            return self
        if not self.name:
            raise ValueError(
                f"step '{self.step_id}': either reuseComponentId, newVersionOfId or a name is required"
            )
        if not self.domains:
            raise ValueError(f"step '{self.step_id}': at least one domain is required to create a new component")
        invalid = [d for d in self.domains if d not in VALID_DOMAINS]
        if invalid:
            raise ValueError(f"step '{self.step_id}': domains must each be one of {VALID_DOMAINS}, got: {invalid}")
        return self


class CreateWorkflowRequestDto(DomainsValidatorMixin, EmptyDescriptionToNoneMixin, CamelModel):
    name: str
    domains: list[str] = Field(json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    # may be a bare .cwl file or a .zip archive - the endpoint detects which
    file: UploadFile
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    #: one entry per workflow step - every step must be configured before the workflow can
    #: be created (the service rejects any that isn't). One multipart form field carrying
    #: a JSON-encoded array.
    component_configs: Json[list[ComponentConfigDto]] = Field(default="[]", validate_default=True)


class AddWorkflowVersionRequestDto(EmptyDescriptionToNoneMixin, CamelModel):
    """An upload as the next version of a workflow - name and domains are its lineage's."""

    # may be a bare .cwl file or a .zip archive - the endpoint detects which
    file: UploadFile
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    #: as for CreateWorkflowRequestDto - one entry per step, JSON-encoded
    component_configs: Json[list[ComponentConfigDto]] = Field(default="[]", validate_default=True)


class ParseWorkflowRequestDto(CamelModel):
    # may be a bare .cwl file or a .zip archive - the endpoint detects which
    file: UploadFile
    #: the workflow the upload is to become the next version of - each step then reports
    #: what it runs there (WorkflowStepPreviewDto.previous)
    parent_id: uuid.UUID | None = None


class StepComponentMatchDto(CamelModel):
    """An existing component a step could bind to instead of creating a new one."""

    component_id: uuid.UUID
    kind: ComponentKind
    name: str
    version: int
    domains: list[str]
    #: fuzzy-match confidence; null for an exact name collision, which isn't a guess
    score: float | None
    #: a deprecated holder of the name can't be reused - a new step can't run it
    status: ComponentStatus


class PreviousStepComponentDto(CamelModel):
    """What a step of an uploaded new version ran in the workflow's newest version."""

    component_id: uuid.UUID
    kind: ComponentKind
    name: str
    version: int
    status: ComponentStatus
    #: the uploaded step's CWL differs from what that component holds
    cwl_changed: bool
    #: the step may become that tool's next version - the caller's own, not from GitHub
    can_add_version: bool


class WorkflowStepPreviewDto(ToolPreviewDto):
    """One workflow step rendered as the component it would become, so the user can review
    and configure it before the workflow is saved. An archive file is one preview however
    many steps run it."""

    #: the config key: the step's path from the top - `inner/generate_graph` for a step of
    #: the nested workflow run by step `inner`; the plain step id at the top level
    step_id: str
    #: a tool, or a nested workflow from the archive - whose own steps follow it, with
    #: parent_step_id pointing back at it
    kind: ComponentKind = ComponentKind.TOOL
    #: the nested workflow whose step first runs it - null at the top level
    parent_step_id: str | None = None
    #: the paths of every step running it, step_id first
    used_by: list[str] = Field(default_factory=list)
    #: "inline" (an inline CommandLineTool) or "archive" (a .cwl file from the uploaded zip)
    origin: str
    #: the archive path of the file, archive origin only
    run_reference: str | None
    suggested_name: str
    #: an existing component that already holds suggested_name - the user must rename or reuse
    name_conflict: StepComponentMatchDto | None
    #: archive origin only - the catalogue tool this step's run: filename matches
    suggested_match: StepComponentMatchDto | None
    #: uploading a new version only - what the same step runs in the workflow's newest version
    previous: PreviousStepComponentDto | None = None


class ParseWorkflowResponseDto(CamelModel):
    #: whether the upload was a .zip archive (vs a bare .cwl file)
    is_zip: bool
    is_self_contained: bool
    #: from label: on the uploaded document  falling back to the filename of the uploaded file -
    #: minus its .cwl extension - or, for a zip, the file that actually contains class: Workflow
    workflow_name: str | None
    #: the workflow document's own doc: field, if any
    description: str | None
    step_count: int
    #: one per component the upload needs a decision for, in tree order: inline tools,
    #: archive files and nested workflows (followed by their own steps). Steps listed in
    #: inline_only_steps or missing_external_refs have no preview.
    component_previews: list[WorkflowStepPreviewDto]
    #: steps whose run: is a plain filename, e.g. "thindata-bytime.cwl"
    external_refs: list[str]
    #: steps whose run: is an inline mapping but not class: CommandLineTool (e.g. an inline
    #: ExpressionTool or sub-Workflow). They stay embedded in the saved pipeline and never
    #: become components, so they need no configuration - informational, not blocking.
    inline_only_steps: list[str]
    #: external_refs not found among the zip's own .cwl files - always [] for a bare
    #: .cwl upload, since there's nothing to cross-check against
    missing_external_refs: list[str]
    #: $import/$include targets resolved from the archive - preserved with the workflow and
    #: written back into every download
    auxiliary_files: list[str]
    #: referenced but absent from the archive - blocks the save, like missing_external_refs
    missing_imports: list[str]
    #: workflow files in the archive the root never runs, at any depth - left out of the upload
    unused_workflow_files: list[str] = Field(default_factory=list)


class UpdateWorkflowStepRequestDto(CamelModel):
    #: the component the step runs - a tool or another workflow; explicit null clears the
    #: match back to unmatched
    component_id: uuid.UUID | None


class WorkflowStepCommandExecuteRequestDto(CamelModel):
    command: WorkflowStepCommandType = Field(..., description="The specific action to perform on the step")
    note: str | None = Field(default=None, description="Optional note for the command execution")
