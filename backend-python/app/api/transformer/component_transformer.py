from typing import Any

from app.api.dto.component import (
    ComponentCommandExecuteRequestDto,
    ComponentCommandTypesApiV1,
    ComponentCreatorDto,
    ComponentDeletionDraftDto,
    ComponentDeletionImpactDto,
    ComponentMatchDto,
    ComponentUsageDto,
    ExistingComponentDto,
)
from app.api.dto.tool import ToolDetailDto, ToolListItemDto
from app.api.dto.workflow import WorkflowDetailDto, WorkflowListItemDto
from app.api.link.component import ComponentLinkBuilder
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.transformer.parameter_transformer import ParameterTransformer
from app.api.transformer.workflow_transformer import WorkflowTransformer
from app.application.commands.commands import ComponentCommand, ComponentCommandType
from app.application.service.compatibility_service import RankedComponent
from app.application.service.components_service import ComponentDeletionImpact, ComponentUsage
from app.domain.models.component import Component
from app.domain.models.user import User
from app.infrastructure.cwl.cwl_parser import inject_description


class ComponentTransformer:
    """The polymorphic view: one entry point per shape, dispatching on the component's
    kind to the matching variant DTO."""

    @staticmethod
    def to_domain_command(dto: ComponentCommandExecuteRequestDto) -> ComponentCommand:
        mapping = {
            ComponentCommandTypesApiV1.ADD_FAVORITE: ComponentCommandType.ADD_FAVORITE,
            ComponentCommandTypesApiV1.REMOVE_FAVORITE: ComponentCommandType.REMOVE_FAVORITE,
            ComponentCommandTypesApiV1.PUBLISH: ComponentCommandType.PUBLISH,
            ComponentCommandTypesApiV1.UNPUBLISH: ComponentCommandType.UNPUBLISH,
            ComponentCommandTypesApiV1.UPDATE_DESCRIPTION: ComponentCommandType.UPDATE_DESCRIPTION,
            ComponentCommandTypesApiV1.UPDATE_DOMAIN: ComponentCommandType.UPDATE_DOMAIN,
        }
        return ComponentCommand(
            type=mapping[dto.command],
            note=dto.note,
            description=dto.description,
            domains=dto.domains,
            publish_components=dto.publish_components,
        )

    @staticmethod
    def to_domains(component: Component) -> list[str]:
        return sorted(d.domain for d in component.domains)

    @staticmethod
    def to_creator(component: Component) -> ComponentCreatorDto | None:
        creator = component.created_by
        if creator is None:
            return None
        return ComponentCreatorDto(
            id=creator.id, email=creator.email, first_name=creator.first_name, last_name=creator.last_name
        )

    @staticmethod
    def to_list_item(
        component: Component,
        is_favorite: bool,
        current_user: User | None,
        include_parameters: bool = False,
    ) -> ToolListItemDto | WorkflowListItemDto:
        shared: dict[str, Any] = dict(
            id=component.id,
            name=component.name,
            description=component.description,
            author_name=component.author_name,
            created_by=ComponentTransformer.to_creator(component),
            version=component.version,
            domains=ComponentTransformer.to_domains(component),
            status=component.status,
            created_at=component.created_at,
            is_favorite=is_favorite,
            parameters=(
                [ParameterTransformer.to_parameter(p, component.ontology_url) for p in component.parameters]
                if include_parameters
                else None
            ),
        )
        if component.is_tool:
            dto = ToolListItemDto(**shared, repo_url=component.repo_url)
        else:
            dto = WorkflowListItemDto(
                **shared,
                step_count=len(component.steps),
                source=component.source,
                draft_id=component.workflow.draft_id if component.workflow is not None else None,
            )
        return ComponentLinkBuilder(current_user).attach_links(dto, component)

    @staticmethod
    def to_ranked_list_item(
        ranked: RankedComponent, is_favorite: bool, current_user: User | None
    ) -> ToolListItemDto | WorkflowListItemDto:
        dto = ComponentTransformer.to_list_item(ranked.component, is_favorite, current_user, include_parameters=True)
        match = ranked.match
        dto.match = ComponentMatchDto(
            score=match.score,
            status=match.status,
            component_id=match.frame.component_id if match.frame else None,
            component_name=match.frame.component_name if match.frame else None,
        )
        return dto

    @staticmethod
    def to_detail(
        component: Component, is_favorite: bool, current_user: User | None
    ) -> ToolDetailDto | WorkflowDetailDto:
        shared: dict[str, Any] = dict(
            id=component.id,
            name=component.name,
            author_name=component.author_name,
            created_by=ComponentTransformer.to_creator(component),
            description=component.description,
            repo_url=component.repo_url,
            repo_commit_sha=component.repo_commit_sha,
            doi=component.doi,
            version=component.version,
            ontology_url=component.ontology_url,
            domains=ComponentTransformer.to_domains(component),
            source=component.source,
            status=component.status,
            parameters=[ParameterTransformer.to_parameter(p, component.ontology_url) for p in component.parameters],
            created_at=component.created_at,
            updated_at=component.updated_at,
            is_favorite=is_favorite,
        )
        if component.is_tool:
            tool = component.tool
            dto = ToolDetailDto(
                **shared,
                cwl_content=inject_description(component.cwl_content, component.description),
                cwl_type=tool.cwl_type if tool is not None else None,
                dockerfile_content=tool.dockerfile_content if tool is not None else None,
                docker_pull_reference=tool.docker_pull_reference if tool is not None else None,
            )
        else:
            dto = WorkflowDetailDto(
                **shared,
                # the pipeline as stored - its description is shown beside it, not injected
                cwl_content=component.cwl_content,
                steps=[WorkflowTransformer.to_step(s, current_user) for s in component.steps],
                draft_id=component.workflow.draft_id if component.workflow is not None else None,
            )
        return ComponentLinkBuilder(current_user).attach_links(dto, component)

    @staticmethod
    def to_existing(component: Component, current_user: User | None) -> ExistingComponentDto:
        return ExistingComponentDto(
            id=component.id,
            kind=component.kind,
            name=component.name,
            version=component.version,
            domains=ComponentTransformer.to_domains(component),
            status=component.status,
            created_at=component.created_at,
            # only a tool lineage takes uploaded versions - a workflow's come from the builder
            can_add_version=component.is_tool and ComponentPermissionValidator(current_user).can_update(component),
        )

    @staticmethod
    def to_usage(usage: ComponentUsage) -> ComponentUsageDto:
        return ComponentUsageDto(
            id=usage.workflow_id,
            name=usage.workflow_name,
            version=usage.workflow_version,
            status=usage.workflow_status,
            component_versions=usage.component_versions,
        )

    @staticmethod
    def to_deletion_impact(impact: ComponentDeletionImpact) -> ComponentDeletionImpactDto:
        return ComponentDeletionImpactDto(
            workflows=[ComponentTransformer.to_usage(u) for u in impact.workflows],
            hidden_workflow_count=impact.hidden_workflow_count,
            drafts=[ComponentDeletionDraftDto(id=d.draft_id, name=d.name) for d in impact.own_drafts],
            other_draft_count=impact.other_draft_count,
        )
