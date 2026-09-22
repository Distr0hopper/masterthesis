from app.api.dto.component import ComponentCreatorDto
from app.api.dto.workflow import (
    ComponentSummaryDto,
    WorkflowCommandExecuteRequestDto,
    WorkflowCommandTypesApiV1,
    WorkflowDetailDto,
    WorkflowListItemDto,
    WorkflowStepCommandExecuteRequestDto,
    WorkflowStepCommandTypesApiV1,
    WorkflowStepDto,
)
from app.api.link.workflow import WorkflowLinkBuilder
from app.api.link.workflow_step import WorkflowStepLinkBuilder
from app.application.commands.commands import WorkflowCommand, WorkflowCommandType, WorkflowStepCommand, WorkflowStepCommandType
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.domain.models.user import User
from app.domain.models.workflow import Workflow
from app.domain.models.workflow_step import WorkflowStep


class WorkflowTransformer:
    @staticmethod
    def to_domain_command(dto: WorkflowCommandExecuteRequestDto) -> WorkflowCommand:
        mapping = {
            WorkflowCommandTypesApiV1.ADD_FAVORITE: WorkflowCommandType.ADD_FAVORITE,
            WorkflowCommandTypesApiV1.REMOVE_FAVORITE: WorkflowCommandType.REMOVE_FAVORITE,
            WorkflowCommandTypesApiV1.PUBLISH: WorkflowCommandType.PUBLISH,
            WorkflowCommandTypesApiV1.UNPUBLISH: WorkflowCommandType.UNPUBLISH,
            WorkflowCommandTypesApiV1.UPDATE_DESCRIPTION: WorkflowCommandType.UPDATE_DESCRIPTION,
        }
        return WorkflowCommand(
            type=mapping[dto.command],
            note=dto.note,
            description=dto.description,
            publish_components=dto.publish_components,
        )

    @staticmethod
    def to_domain_step_command(dto: WorkflowStepCommandExecuteRequestDto) -> WorkflowStepCommand:
        mapping = {
            WorkflowStepCommandTypesApiV1.CONFIRM: WorkflowStepCommandType.CONFIRM,
        }
        return WorkflowStepCommand(type=mapping[dto.command], note=dto.note)

    @staticmethod
    def to_list_item(workflow: Workflow, is_favorite: bool, current_user: User | None) -> WorkflowListItemDto:
        dto = WorkflowListItemDto(
            id=workflow.id,
            name=workflow.name,
            description=workflow.description,
            domains=[d.domain for d in workflow.domains],
            step_count=len(workflow.steps),
            is_favorite=is_favorite,
            status=workflow.status,
            source=workflow.source,
            draft_id=workflow.draft_id,
            created_at=workflow.created_at,
        )
        return WorkflowLinkBuilder(current_user).attach_links(dto, workflow)

    @staticmethod
    def to_step(step: WorkflowStep, current_user: User | None) -> WorkflowStepDto:
        dto = WorkflowStepDto(
            id=step.id,
            step_id=step.step_id,
            run_reference=step.run_reference,
            step_order=step.step_order,
            component=ComponentSummaryDto(
                id=step.component.id,
                name=step.component.name,
                version=step.component.version,
                domains=sorted(d.domain for d in step.component.domains),
                status=step.component.status,
                can_publish=ComponentPermissionValidator(current_user).can_update(step.component),
            )
            if step.component is not None
            else None,
            match_status=step.match_status,
            match_score=step.match_score,
        )
        return WorkflowStepLinkBuilder(current_user).attach_links(dto, step)

    @staticmethod
    def to_detail(workflow: Workflow, is_favorite: bool, current_user: User | None) -> WorkflowDetailDto:
        dto = WorkflowDetailDto(
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
            steps=[WorkflowTransformer.to_step(s, current_user) for s in workflow.steps],
            is_favorite=is_favorite,
            status=workflow.status,
            source=workflow.source,
            draft_id=workflow.draft_id,
            cwl_content=workflow.cwl_content,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
        )
        return WorkflowLinkBuilder(current_user).attach_links(dto, workflow)
