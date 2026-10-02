from app.api.dto.workflow import (
    ComponentSummaryDto,
    StepComponentMatchDto,
    WorkflowStepCommandExecuteRequestDto,
    WorkflowStepCommandTypesApiV1,
    WorkflowStepDto,
    WorkflowStepPreviewDto,
)
from app.api.link.workflow_step import WorkflowStepLinkBuilder
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.transformer.parameter_transformer import ParameterTransformer
from app.application.commands.commands import WorkflowStepCommand, WorkflowStepCommandType
from app.application.service.workflows_service import ComponentMatch, ComponentPreview
from app.domain.models.component import Component
from app.domain.models.user import User
from app.domain.models.workflow_step import WorkflowStep


class WorkflowTransformer:
    """What only a workflow has: its steps - the edges to the child components it runs."""

    @staticmethod
    def to_domain_step_command(dto: WorkflowStepCommandExecuteRequestDto) -> WorkflowStepCommand:
        mapping = {
            WorkflowStepCommandTypesApiV1.CONFIRM: WorkflowStepCommandType.CONFIRM,
        }
        return WorkflowStepCommand(type=mapping[dto.command], note=dto.note)

    @staticmethod
    def to_summary(component: Component, current_user: User | None) -> ComponentSummaryDto:
        return ComponentSummaryDto(
            id=component.id,
            kind=component.kind,
            name=component.name,
            version=component.version,
            domains=sorted(d.domain for d in component.domains),
            status=component.status,
            can_publish=ComponentPermissionValidator(current_user).can_update(component),
        )

    @staticmethod
    def to_step(step: WorkflowStep, current_user: User | None) -> WorkflowStepDto:
        dto = WorkflowStepDto(
            id=step.id,
            step_id=step.step_id,
            run_reference=step.run_reference,
            step_order=step.step_order,
            component=WorkflowTransformer.to_summary(step.component, current_user)
            if step.component is not None
            else None,
            match_status=step.match_status,
            match_score=step.match_score,
        )
        return WorkflowStepLinkBuilder(current_user).attach_links(dto, step)

    @staticmethod
    def to_step_component_match(match: ComponentMatch | None) -> StepComponentMatchDto | None:
        if match is None:
            return None
        return StepComponentMatchDto(
            component_id=match.component_id,
            kind=match.kind,
            name=match.name,
            version=match.version,
            domains=match.domains,
            score=match.score,
        )

    @staticmethod
    def to_step_preview(preview: ComponentPreview) -> WorkflowStepPreviewDto:
        return WorkflowStepPreviewDto(
            step_id=preview.step_id,
            origin=preview.origin,
            run_reference=preview.run_reference,
            suggested_name=preview.suggested_name,
            description=preview.description,
            cwl_content=preview.cwl_content,
            cwl_type=preview.cwl_type,
            dockerfile_content=preview.dockerfile_content,
            docker_pull_reference=preview.docker_pull_reference,
            ontology_url=preview.ontology_url,
            parameters=[
                ParameterTransformer.to_preview_parameter(parameter, preview.step_id, preview.ontology_url)
                for parameter in preview.parameters
            ],
            name_conflict=WorkflowTransformer.to_step_component_match(preview.name_conflict),
            suggested_match=WorkflowTransformer.to_step_component_match(preview.suggested_match),
        )
