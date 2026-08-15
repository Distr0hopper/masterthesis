import uuid
from datetime import datetime

from fastapi import UploadFile
from pydantic import Field, field_validator

from app.api.dto.base import CamelModel
from app.api.dto.component import ComponentCreatorDto
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.workflow import MAX_DESCRIPTION_LENGTH
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


class WorkflowStepDto(CamelModel):
    id: uuid.UUID
    step_id: str
    run_reference: str
    step_order: int
    component: ComponentSummaryDto | None
    match_status: StepMatchStatus
    match_score: float | None


class WorkflowListItemDto(CamelModel):
    id: uuid.UUID
    name: str
    description: str | None
    domains: list[str]
    step_count: int
    created_at: datetime


class WorkflowDetailDto(CamelModel):
    id: uuid.UUID
    name: str
    description: str | None
    domains: list[str]
    created_by: ComponentCreatorDto | None
    steps: list[WorkflowStepDto]
    created_at: datetime
    updated_at: datetime


class CreateWorkflowRequestDto(WorkflowDomainsValidatorMixin, EmptyWorkflowDescriptionToNoneMixin, CamelModel):
    name: str
    domains: list[str] = Field(json_schema_extra={"items": {"enum": VALID_DOMAINS}})
    zip_file: UploadFile
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


class UpdateWorkflowStepRequestDto(CamelModel):
    # explicit null clears the match back to unmatched
    component_id: uuid.UUID | None
