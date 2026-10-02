import uuid

from app.api.dto.tool import (
    AddVersionRequestDto,
    CreateToolRequestDto,
    ToolCommandExecuteRequestDto,
    ToolCommandTypesApiV1,
    ToolPreviewDto,
)
from app.api.transformer.parameter_transformer import ParameterTransformer
from app.application.commands.commands import ToolCommand, ToolCommandType
from app.application.service.tools_service import ParsedTool
from app.domain.models.component import Component, ComponentKind, ComponentSource
from app.domain.models.component_domain import ComponentDomain


class ToolTransformer:
    """What only a tool has: its upload/packaging requests, previews and commands."""

    @staticmethod
    def to_domain_command(dto: ToolCommandExecuteRequestDto) -> ToolCommand:
        mapping = {
            ToolCommandTypesApiV1.REPACKAGE: ToolCommandType.REPACKAGE,
            ToolCommandTypesApiV1.UPDATE_FORMAT_LABELS: ToolCommandType.UPDATE_FORMAT_LABELS,
        }
        return ToolCommand(
            type=mapping[dto.command],
            note=dto.note,
            format_labels=(
                ParameterTransformer.to_format_labels(dto.format_labels) if dto.format_labels is not None else None
            ),
        )

    @staticmethod
    def from_create_dto(dto: CreateToolRequestDto, cwl_content: str, created_by_id: uuid.UUID) -> Component:
        return Component(
            kind=ComponentKind.TOOL,
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
            kind=ComponentKind.TOOL,
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
    def to_preview_fields(parsed: ParsedTool) -> dict:
        """The ToolPreviewDto fields of a parse result - shared with PackagePreviewDto, which extends it."""
        return dict(
            cwl_content=parsed.cwl_content,
            cwl_type=parsed.cwl_type,
            description=parsed.description,
            dockerfile_content=parsed.dockerfile_content,
            docker_pull_reference=parsed.docker_pull_reference,
            ontology_url=parsed.ontology_url,
            parameters=[
                ParameterTransformer.to_preview_parameter(p, "preview", parsed.ontology_url) for p in parsed.parameters
            ],
        )

    @staticmethod
    def to_preview(parsed: ParsedTool) -> ToolPreviewDto:
        return ToolPreviewDto(**ToolTransformer.to_preview_fields(parsed))
