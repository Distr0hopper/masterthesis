import uuid

from app.api.dto.component import (
    AddVersionRequestDto,
    ComponentCommandExecuteRequestDto,
    ComponentCommandTypesApiV1,
    ComponentCreatorDto,
    ComponentDetailDto,
    ComponentListItemDto,
    CreateComponentRequestDto,
    ParameterDto,
)
from app.api.link.component import ComponentLinkBuilder
from app.application.commands.commands import ComponentCommand, ComponentCommandType
from app.domain.models.component import Component, ComponentSource
from app.domain.models.parameter import Parameter
from app.domain.models.user import User
from app.infrastructure.cwl.cwl_parser import inject_description


class ComponentTransformer:
    @staticmethod
    def to_domain_command(dto: ComponentCommandExecuteRequestDto) -> ComponentCommand:
        mapping = {
            ComponentCommandTypesApiV1.ADD_FAVORITE: ComponentCommandType.ADD_FAVORITE,
            ComponentCommandTypesApiV1.REMOVE_FAVORITE: ComponentCommandType.REMOVE_FAVORITE,
            ComponentCommandTypesApiV1.REPACKAGE: ComponentCommandType.REPACKAGE,
            ComponentCommandTypesApiV1.PUBLISH: ComponentCommandType.PUBLISH,
            ComponentCommandTypesApiV1.UNPUBLISH: ComponentCommandType.UNPUBLISH,
            ComponentCommandTypesApiV1.UPDATE_DESCRIPTION: ComponentCommandType.UPDATE_DESCRIPTION,
            ComponentCommandTypesApiV1.UPDATE_DOMAIN: ComponentCommandType.UPDATE_DOMAIN,
        }
        return ComponentCommand(
            type=mapping[dto.command], note=dto.note, description=dto.description, domain=dto.domain
        )

    @staticmethod
    def from_create_dto(dto: CreateComponentRequestDto, cwl_content: str, created_by_id: uuid.UUID) -> Component:
        return Component(
            name=dto.name,
            domain=dto.domain,
            author_name=dto.author_name,
            created_by_id=created_by_id,
            repo_url=dto.repo_url,
            repo_commit_sha=dto.repo_commit_sha,
            description=dto.description,
            version=1,
            cwl_content=cwl_content,
            source=ComponentSource.MANUAL_UPLOAD,
        )

    @staticmethod
    def from_add_version_dto(parent: Component, dto: AddVersionRequestDto, cwl_content: str) -> Component:
        return Component(
            name=parent.name,
            author_name=parent.author_name,
            created_by_id=parent.created_by_id,
            repo_url=parent.repo_url,
            repo_commit_sha=dto.repo_commit_sha,
            cwl_content=cwl_content,
            description=dto.description,
            source=parent.source,
            domain=parent.domain,
        )

    @staticmethod
    def to_list_item(
        component: Component,
        is_favorite: bool,
        current_user: User | None,
        include_parameters: bool = False,
    ) -> ComponentListItemDto:
        dto = ComponentListItemDto(
            id=component.id,
            name=component.name,
            description=component.description,
            author_name=component.author_name,
            repo_url=component.repo_url,
            version=component.version,
            domain=component.domain,
            status=component.status,
            created_at=component.created_at,
            is_favorite=is_favorite,
            parameters=(
                [ComponentTransformer.to_parameter(p) for p in component.parameters] if include_parameters else None
            ),
        )
        return ComponentLinkBuilder(current_user).attach_links(dto, component)

    @staticmethod
    def to_parameter(parameter: Parameter) -> ParameterDto:
        return ParameterDto(
            id=parameter.id,
            name=parameter.name,
            cwl_type=parameter.cwl_type,
            default_value=parameter.default_value,
            description=parameter.description,
            format=parameter.format,
            format_label=parameter.format_label,
            direction=parameter.direction,
        )

    @staticmethod
    def to_detail(component: Component, is_favorite: bool, current_user: User | None) -> ComponentDetailDto:
        dto = ComponentDetailDto(
            id=component.id,
            name=component.name,
            author_name=component.author_name,
            created_by=ComponentCreatorDto(
                id=component.created_by.id,
                email=component.created_by.email,
                first_name=component.created_by.first_name,
                last_name=component.created_by.last_name,
            )
            if component.created_by
            else None,
            description=component.description,
            repo_url=component.repo_url,
            repo_commit_sha=component.repo_commit_sha,
            doi=component.doi,
            version=component.version,
            cwl_content=inject_description(component.cwl_content, component.description),
            cwl_type=component.cwl_type,
            dockerfile_content=component.dockerfile_content,
            docker_pull_reference=component.docker_pull_reference,
            domain=component.domain,
            source=component.source,
            status=component.status,
            parameters=[ComponentTransformer.to_parameter(p) for p in component.parameters],
            created_at=component.created_at,
            updated_at=component.updated_at,
            is_favorite=is_favorite,
        )
        return ComponentLinkBuilder(current_user).attach_links(dto, component)