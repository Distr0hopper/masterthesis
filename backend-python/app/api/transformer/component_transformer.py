import uuid

from app.api.dto.component import ComponentCreatorDto, ComponentDetailDto, ComponentListItemDto, CreateComponentRequestDto, ParameterDto
from app.domain.models.component import Component, ComponentSource
from app.domain.models.parameter import Parameter
from app.infrastructure.cwl.cwl_parser import inject_description


class ComponentTransformer:
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
    def to_list_item(component: Component) -> ComponentListItemDto:
        return ComponentListItemDto(
            id=component.id,
            name=component.name,
            author_name=component.author_name,
            repo_url=component.repo_url,
            repo_commit_sha=component.repo_commit_sha,
            version=component.version,
            domain=component.domain,
            source=component.source,
            created_at=component.created_at,
        )

    @staticmethod
    def to_parameter(parameter: Parameter) -> ParameterDto:
        return ParameterDto(
            id=parameter.id,
            name=parameter.name,
            cwl_type=parameter.cwl_type,
            default_value=parameter.default_value,
            description=parameter.description,
            direction=parameter.direction,
        )

    @staticmethod
    def to_detail(component: Component) -> ComponentDetailDto:
        return ComponentDetailDto(
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
            domain=component.domain,
            source=component.source,
            parameters=[ComponentTransformer.to_parameter(p) for p in component.parameters],
            created_at=component.created_at,
        )