from app.api.dto.component import ComponentCreatorDto
from app.api.dto.workflow import (
    ComponentSummaryDto,
    WorkflowDetailDto,
    WorkflowListItemDto,
    WorkflowStepDto,
)
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import WorkflowStep


class WorkflowTransformer:
    @staticmethod
    def to_list_item(workflow: Workflow) -> WorkflowListItemDto:
        return WorkflowListItemDto(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            domains=[d.domain for d in workflow.domains],
            step_count=len(workflow.steps),
            created_at=workflow.created_at,
        )

    @staticmethod
    def to_step(step: WorkflowStep) -> WorkflowStepDto:
        return WorkflowStepDto(
            id=step.id,
            step_id=step.step_id,
            run_reference=step.run_reference,
            step_order=step.step_order,
            component=ComponentSummaryDto(
                id=step.component.id,
                name=step.component.name,
                version=step.component.version,
                domain=step.component.domain,
            )
            if step.component is not None
            else None,
            match_status=step.match_status,
            match_score=step.match_score,
        )

    @staticmethod
    def to_detail(workflow: Workflow) -> WorkflowDetailDto:
        return WorkflowDetailDto(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            domains=[d.domain for d in workflow.domains],
            created_by=ComponentCreatorDto(
                id=workflow.created_by.id,
                email=workflow.created_by.email,
                first_name=workflow.created_by.first_name,
                last_name=workflow.created_by.last_name,
            )
            if workflow.created_by
            else None,
            steps=[WorkflowTransformer.to_step(s) for s in workflow.steps],
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )
