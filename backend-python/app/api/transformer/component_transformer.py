import uuid

from app.api.dto.component import (
    AddVersionRequestDto,
    ComponentCommandExecuteRequestDto,
    ComponentCommandTypesApiV1,
    ComponentCreatorDto,
    ComponentDetailDto,
    ComponentListItemDto,
    ComponentMatchDto,
    CreateComponentRequestDto,
    FormatLabelDto,
    ParameterDto,
    PreviewParameterDto,
)
from app.api.link.component import ComponentLinkBuilder
from app.application.commands.commands import ComponentCommand, ComponentCommandType, ManualFormatLabel
from app.application.service.compatibility_service import RankedComponent
from app.domain.compatibility.format_label import accepts_manual_format_label, format_label_source
from app.domain.models.component import Component, ComponentSource
from app.domain.models.component_domain import ComponentDomain
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
            ComponentCommandTypesApiV1.UPDATE_FORMAT_LABELS: ComponentCommandType.UPDATE_FORMAT_LABELS,
        }
        return ComponentCommand(
            type=mapping[dto.command],
            note=dto.note,
            description=dto.description,
            domains=dto.domains,
            format_labels=(
                ComponentTransformer.to_format_labels(dto.format_labels) if dto.format_labels is not None else None
            ),
        )

    @staticmethod
    def to_format_labels(dtos: list[FormatLabelDto]) -> list[ManualFormatLabel]:
        return [ManualFormatLabel(name=d.name, direction=d.direction, label=d.label) for d in dtos]

    @staticmethod
    def to_preview_parameter(parameter: Parameter, id_prefix: str, ontology_url: str | None) -> PreviewParameterDto:
        return PreviewParameterDto(
            id=f"{id_prefix}:{parameter.direction.value}:{parameter.name}",
            name=parameter.name,
            cwl_type=parameter.cwl_type,
            default_value=parameter.default_value,
            description=parameter.description,
            format=parameter.format,
            format_label=parameter.format_label,
            ontology_url=ontology_url,
            format_label_source=format_label_source(parameter, ontology_url),
            accepts_manual_format_label=accepts_manual_format_label(parameter, ontology_url),
            direction=parameter.direction,
        )

    @staticmethod
    def to_domains(component: Component) -> list[str]:
        return sorted(d.domain for d in component.domains)

    @staticmethod
    def from_create_dto(dto: CreateComponentRequestDto, cwl_content: str, created_by_id: uuid.UUID) -> Component:
        return Component(
            name=dto.name,
            domains=[ComponentDomain(domain=d) for d in dto.domains],
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
            domains=[ComponentDomain(domain=d.domain) for d in parent.domains],
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
            created_by=ComponentTransformer.to_creator(component),
            repo_url=component.repo_url,
            version=component.version,
            domains=ComponentTransformer.to_domains(component),
            status=component.status,
            created_at=component.created_at,
            is_favorite=is_favorite,
            parameters=(
                [ComponentTransformer.to_parameter(p, component.ontology_url) for p in component.parameters]
                if include_parameters
                else None
            ),
        )
        return ComponentLinkBuilder(current_user).attach_links(dto, component)

    @staticmethod
    def to_ranked_list_item(
        ranked: RankedComponent, is_favorite: bool, current_user: User | None
    ) -> ComponentListItemDto:
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
    def to_parameter(parameter: Parameter, ontology_url: str | None) -> ParameterDto:
        return ParameterDto(
            id=parameter.id,
            name=parameter.name,
            cwl_type=parameter.cwl_type,
            default_value=parameter.default_value,
            description=parameter.description,
            format=parameter.format,
            format_label=parameter.format_label,
            ontology_url=ontology_url,
            format_label_source=format_label_source(parameter, ontology_url),
            accepts_manual_format_label=accepts_manual_format_label(parameter, ontology_url),
            direction=parameter.direction,
        )

    @staticmethod
    def to_creator(component: Component) -> ComponentCreatorDto | None:
        creator = component.created_by
        if creator is None:
            return None
        return ComponentCreatorDto(
            id=creator.id, email=creator.email, first_name=creator.first_name, last_name=creator.last_name
        )

    @staticmethod
    def to_detail(component: Component, is_favorite: bool, current_user: User | None) -> ComponentDetailDto:
        dto = ComponentDetailDto(
            id=component.id,
            name=component.name,
            author_name=component.author_name,
            created_by=ComponentTransformer.to_creator(component),
            description=component.description,
            repo_url=component.repo_url,
            repo_commit_sha=component.repo_commit_sha,
            doi=component.doi,
            version=component.version,
            cwl_content=inject_description(component.cwl_content, component.description),
            cwl_type=component.cwl_type,
            dockerfile_content=component.dockerfile_content,
            docker_pull_reference=component.docker_pull_reference,
            ontology_url=component.ontology_url,
            domains=ComponentTransformer.to_domains(component),
            source=component.source,
            status=component.status,
            parameters=[ComponentTransformer.to_parameter(p, component.ontology_url) for p in component.parameters],
            created_at=component.created_at,
            updated_at=component.updated_at,
            is_favorite=is_favorite,
        )
        return ComponentLinkBuilder(current_user).attach_links(dto, component)