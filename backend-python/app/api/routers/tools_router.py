"""/tools - what only a tool, the leaf of the composite, has: uploading a single CWL
document, packaging from a repository, versions, format labels and the run bundle.
Listing, reading, publishing and deleting are shared with workflows under /components."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status
from fastapi.responses import Response

from app.api.dto.common import ErrorResponse
from app.api.dto.tool import (
    AddVersionRequestDto,
    CreateToolRequestDto,
    PackagePreviewDto,
    PackagePreviewRequestDto,
    PackageToolRequestDto,
    ParseToolRequestDto,
    ToolCommandExecuteRequestDto,
    ToolDetailDto,
    ToolPreviewDto,
)
from app.api.exception.exceptions import ForbiddenException
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.transformer.component_transformer import ComponentTransformer
from app.api.transformer.parameter_transformer import ParameterTransformer
from app.api.transformer.tool_transformer import ToolTransformer
from app.application.service.auth_service import AuthService
from app.application.service.components_service import ComponentsService
from app.application.service.tools_service import ToolsService
from app.domain.models.component import ComponentKind
from app.domain.models.user import User

router = APIRouter(prefix="/tools", tags=["tools"])
logger = logging.getLogger("app.api.routers.tools_router")

MAX_CWL_FILE_SIZE = 1024 * 1024


def _require_size(content: bytes) -> None:
    if len(content) > MAX_CWL_FILE_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_CWL_FILE_SIZE} bytes)",
        )


@router.post(
    "/parse",
    response_model=ToolPreviewDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid CWL or file too large"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
    },
)
async def parse_tool(
    dto: Annotated[ParseToolRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    tools_service: Annotated[ToolsService, Depends(ToolsService.get_service)],
) -> ToolPreviewDto:
    """Read an uploaded .cwl without persisting it, so the user can review the tool
    before creating it. Mirrors POST /workflows/parse."""
    content = await dto.cwl_file.read()
    _require_size(content)

    logger.info(f"Parsing tool upload '{dto.cwl_file.filename}' for user {current_user.id}")
    return ToolTransformer.to_preview(await tools_service.parse_cwl(content))


@router.post(
    "",
    response_model=ToolDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid CWL content or file too large"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "A component with this name already exists"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def create(
    dto: Annotated[CreateToolRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    tools_service: Annotated[ToolsService, Depends(ToolsService.get_service)],
) -> ToolDetailDto:
    validator = ComponentPermissionValidator(current_user)
    if not validator.can_create():
        raise ForbiddenException("Insufficient permission to create a tool")

    content = await dto.cwl_file.read()
    _require_size(content)

    logger.info(f"Creating tool '{dto.name}' for user {current_user.id}")
    tool = ToolTransformer.from_create_dto(dto, content.decode("utf-8"), current_user.id)
    created = await tools_service.create_manual(
        tool, format_labels=ParameterTransformer.to_format_labels(dto.format_labels)
    )
    logger.info(f"Created tool {created.id} ('{created.name}' v{created.version})")
    return ComponentTransformer.to_detail(created, is_favorite=False, current_user=current_user)


@router.post(
    "/package/preview",
    response_model=PackagePreviewDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid URL or packaging failed"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "The repo is already packaged as a tool the caller cannot see",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ErrorResponse, "description": "Packaging service unreachable"},
    },
)
async def package_preview(
    dto: PackagePreviewRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    tools_service: Annotated[ToolsService, Depends(ToolsService.get_service)],
) -> PackagePreviewDto:
    """Package a GitHub repo without persisting it, so the user can review the generated
    tool (and label its File ports) before POST /tools/package creates it.
    Mirrors POST /tools/parse."""
    logger.info(f"Previewing package of {dto.repo_url} for user {current_user.id}")
    preview = await tools_service.preview_package(dto.repo_url)
    existing = preview.existing
    if existing is not None and not ComponentPermissionValidator(current_user).can_read(existing):
        raise ForbiddenException("This repository is already packaged as another user's tool")

    return PackagePreviewDto(
        **ToolTransformer.to_preview_fields(preview.parsed),
        repo_name=preview.repo_name,
        repo_url=preview.repo_url,
        commit_sha=preview.commit_sha,
        author=preview.author,
        existing=None if existing is None else ComponentTransformer.to_existing(existing, current_user),
        already_packaged=preview.already_packaged,
    )


@router.post(
    "/package",
    response_model=ToolDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid URL or packaging failed"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {
            "model": ErrorResponse,
            "description": "Not the creator of this lineage (only applies when repoUrl already exists)",
        },
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "This exact commit is already packaged, the name collides with an existing component, "
            "or the repo changed since expectedCommitSha was reviewed",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def package(
    dto: PackageToolRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    tools_service: Annotated[ToolsService, Depends(ToolsService.get_service)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ToolDetailDto:
    existing = await tools_service.find_tool_by_repo_url(dto.repo_url)
    format_labels = ParameterTransformer.to_format_labels(dto.format_labels)
    logger.info(f"Packaging tool from {dto.repo_url}")

    if existing is not None:
        if not ComponentPermissionValidator(current_user).can_update(existing):
            logger.warning(f"User {current_user.id} not permitted to package a new version of repo {dto.repo_url}")
            raise ForbiddenException("Insufficient permission to package a new version of this tool")
        tool = await tools_service.package_next_version(
            existing, dto.description, format_labels, dto.expected_commit_sha
        )
    else:
        tool = await tools_service.create_from_url(
            dto.repo_url,
            dto.domains,
            dto.description,
            current_user.id,
            name=dto.name,
            format_labels=format_labels,
            expected_commit_sha=dto.expected_commit_sha,
        )

    logger.info(f"Packaging complete: '{tool.name}' v{tool.version} ({tool.id})")
    favorited_names = await components_service.favorited_names(current_user)
    return ComponentTransformer.to_detail(tool, tool.name in favorited_names, current_user)


@router.post(
    "/{tool_id}/versions",
    response_model=ToolDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid CWL content or file too large"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this tool"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Tool not found"},
    },
)
async def add_version(
    tool_id: uuid.UUID,
    dto: Annotated[AddVersionRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    tools_service: Annotated[ToolsService, Depends(ToolsService.get_service)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ToolDetailDto:
    parent = await components_service.get_component(tool_id, ComponentKind.TOOL)

    if not ComponentPermissionValidator(current_user).can_update(parent):
        logger.warning(f"User {current_user.id} not permitted to add version to tool {tool_id}")
        raise ForbiddenException("Insufficient permission to add a version to this tool")

    content = await dto.cwl_file.read()
    _require_size(content)

    draft = ToolTransformer.from_add_version_dto(parent, dto, content.decode("utf-8"))
    tool = await tools_service.add_manual_version(draft)
    logger.info(f"Added version {tool.version} to tool '{parent.name}' ({tool.id})")
    favorited_names = await components_service.favorited_names(current_user)
    return ComponentTransformer.to_detail(tool, tool.name in favorited_names, current_user)


@router.post(
    "/{tool_id}/commands",
    response_model=ToolDetailDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Command is missing a payload field it requires (e.g. UPDATE_FORMAT_LABELS without "
            "formatLabels), or REPACKAGE of a manual upload",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permission for this command"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Tool not found"},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "REPACKAGE found no new commit"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Unknown command"},
    },
)
async def execute_command(
    tool_id: uuid.UUID,
    dto: ToolCommandExecuteRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    tools_service: Annotated[ToolsService, Depends(ToolsService.get_service)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ToolDetailDto:
    tool = await components_service.get_visible_component(tool_id, current_user, ComponentKind.TOOL)
    command = ToolTransformer.to_domain_command(dto)

    if not ComponentPermissionValidator(current_user).can_execute_tool(tool, command.type):
        logger.warning(f"User {current_user.id} not permitted to execute {command.type} on tool {tool_id}")
        raise ForbiddenException(f"Insufficient permission to execute {command.type} on this tool")

    updated = await tools_service.execute_command(tool, command)
    logger.info(f"Executed command {command.type} on tool {tool_id}")
    favorited_names = await components_service.favorited_names(current_user)
    return ComponentTransformer.to_detail(updated, updated.name in favorited_names, current_user)


@router.get(
    "/{tool_id}/bundle",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Tool not found"}},
)
async def bundle(
    tool_id: uuid.UUID,
    tools_service: Annotated[ToolsService, Depends(ToolsService.get_service)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> Response:
    """The tool ready to run: its .cwl, an inputs.yaml template and its imported files."""
    tool = await components_service.get_visible_component(tool_id, current_user, ComponentKind.TOOL)
    filename, content = await tools_service.get_bundle(tool)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
