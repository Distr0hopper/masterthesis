import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import Response

from app.api.dto.common import ErrorResponse, MyItemsResponseDtoV1, build_my_items_response
from app.api.dto.pagination import ListQueryPaginationDtoV1, PaginatedResponseDtoV1, build_paginated_response
from app.api.dto.workflow import (
    ComponentMatchDto,
    WorkflowStepPreviewDto,
    CreateWorkflowRequestDto,
    ParseWorkflowRequestDto,
    ParseWorkflowResponseDto,
    UpdateWorkflowStepRequestDto,
    WorkflowCommandExecuteRequestDto,
    WorkflowDetailDto,
    WorkflowListItemDto,
    WorkflowStepCommandExecuteRequestDto,
    WorkflowStepDto,
)
from app.api.exception.exceptions import ForbiddenException
from app.api.permission.workflow_permission_validator import WorkflowPermissionValidator
from app.api.transformer.component_transformer import ComponentTransformer
from app.api.transformer.workflow_transformer import WorkflowTransformer
from app.application.exception.favorites_exceptions import FavoritesRequireAuthError
from app.application.service.auth_service import AuthService
from app.application.service.favorites_service import FavoritesService
from app.application.service.workflows_service import ComponentConfig, ComponentMatch, ComponentPreview, WorkflowsService
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.user import User
from app.domain.models.workflow import WorkflowStatus
from app.domain.pagination.pagination import DEFAULT_LIMIT, MAX_LIMIT, PaginatedList
from app.domain.repository.workflows_repository import WorkflowListFilter

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger("app.api.routers.workflows_router")

MAX_WORKFLOW_ZIP_SIZE = 10 * 1024 * 1024


def _to_component_match_dto(match: ComponentMatch | None) -> ComponentMatchDto | None:
    if match is None:
        return None
    return ComponentMatchDto(
        component_id=match.component_id,
        name=match.name,
        version=match.version,
        domains=match.domains,
        score=match.score,
    )


def _to_workflow_step_preview_dto(preview: ComponentPreview) -> WorkflowStepPreviewDto:
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
        parameters=[
            ComponentTransformer.to_preview_parameter(parameter, preview.step_id)
            for parameter in preview.parameters
        ],
        name_conflict=_to_component_match_dto(preview.name_conflict),
        suggested_match=_to_component_match_dto(preview.suggested_match),
    )


async def _favorited_ids(favorites_service: FavoritesService, user: User | None) -> set[str]:
    return await favorites_service.get_favorited_workflow_ids(user.id) if user is not None else set()


@router.get("", response_model=PaginatedResponseDtoV1[WorkflowListItemDto])
async def list_workflows(
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    pagination_dto: Annotated[ListQueryPaginationDtoV1, Depends()],
    domain: Annotated[str | None, Query(json_schema_extra={"enum": VALID_DOMAINS})] = None,
    search: Annotated[str | None, Query()] = None,
    favorites_only: Annotated[bool, Query(alias="favoritesOnly")] = False,
) -> PaginatedResponseDtoV1[WorkflowListItemDto]:
    if favorites_only and current_user is None:
        raise FavoritesRequireAuthError()

    pagination = pagination_dto.to_domain()
    favorited_by = current_user.id if favorites_only and current_user is not None else None
    filter = WorkflowListFilter(domain=domain, search=search, favorited_by=favorited_by)
    workflows, total = await workflows_service.list_workflows(filter, pagination)

    favorited_ids = await _favorited_ids(favorites_service, current_user)
    items = [WorkflowTransformer.to_list_item(w, str(w.id) in favorited_ids, current_user) for w in workflows]
    return build_paginated_response(items, total, pagination)


@router.get(
    "/mine",
    response_model=MyItemsResponseDtoV1[WorkflowListItemDto],
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"}},
)
async def list_my_workflows(
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    published_offset: Annotated[int, Query(alias="publishedOffset", ge=0)] = 0,
    unpublished_offset: Annotated[int, Query(alias="unpublishedOffset", ge=0)] = 0,
) -> MyItemsResponseDtoV1[WorkflowListItemDto]:
    published_pagination = PaginatedList(limit=limit, offset=published_offset)
    unpublished_pagination = PaginatedList(limit=limit, offset=unpublished_offset)

    published_workflows, published_total = await workflows_service.list_my_workflows_by_status(
        current_user.id, WorkflowStatus.VALIDATED, published_pagination
    )
    unpublished_workflows, unpublished_total = await workflows_service.list_my_workflows_by_status(
        current_user.id, WorkflowStatus.PENDING_VALIDATION, unpublished_pagination
    )

    favorited_ids = await _favorited_ids(favorites_service, current_user)
    return build_my_items_response(
        (
            [WorkflowTransformer.to_list_item(w, str(w.id) in favorited_ids, current_user) for w in published_workflows],
            published_total,
        ),
        published_pagination,
        (
            [
                WorkflowTransformer.to_list_item(w, str(w.id) in favorited_ids, current_user)
                for w in unpublished_workflows
            ],
            unpublished_total,
        ),
        unpublished_pagination,
    )


@router.get("/latest", response_model=list[WorkflowListItemDto])
async def list_latest_workflows(
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    limit: int = 6,
) -> list[WorkflowListItemDto]:
    workflows = await workflows_service.get_latest_workflows(limit)
    favorited_ids = await _favorited_ids(favorites_service, current_user)
    return [WorkflowTransformer.to_list_item(w, str(w.id) in favorited_ids, current_user) for w in workflows]


@router.post(
    "",
    response_model=WorkflowDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid workflow file/archive, file too large, or unsupported inline step",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "A configured component's name already exists",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def create(
    dto: Annotated[CreateWorkflowRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> WorkflowDetailDto:
    validator = WorkflowPermissionValidator(current_user)
    if not validator.can_create():
        raise ForbiddenException("Insufficient permission to create a workflow")

    content = await dto.file.read()
    if len(content) > MAX_WORKFLOW_ZIP_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_WORKFLOW_ZIP_SIZE} bytes)",
        )

    configs_by_step = {
        c.step_id: ComponentConfig(
            step_id=c.step_id,
            reuse_component_id=c.reuse_component_id,
            name=c.name,
            domains=c.domains,
            description=c.description,
        )
        for c in dto.component_configs
    }
    logger.info(f"Creating workflow '{dto.name}' for user {current_user.id}")
    workflow = await workflows_service.create_from_upload(
        content,
        dto.file.filename,
        dto.name,
        dto.description,
        dto.domains,
        configs_by_step,
        current_user.id,
    )
    logger.info(f"Created workflow {workflow.id} ('{workflow.name}') with {len(workflow.steps)} steps")
    return WorkflowTransformer.to_detail(workflow, False, current_user)


@router.post(
    "/parse",
    response_model=ParseWorkflowResponseDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid CWL/zip content or file too large",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
    },
)
async def parse_workflow(
    dto: Annotated[ParseWorkflowRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> ParseWorkflowResponseDto:
    content = await dto.file.read()
    if len(content) > MAX_WORKFLOW_ZIP_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_WORKFLOW_ZIP_SIZE} bytes)",
        )

    logger.info(f"Parsing workflow upload '{dto.file.filename}' for user {current_user.id}")
    preview = await workflows_service.parse_workflow_upload(content, dto.file.filename)

    return ParseWorkflowResponseDto(
        is_zip=preview.is_zip,
        is_self_contained=preview.is_self_contained,
        workflow_name=preview.workflow_name,
        step_count=preview.step_count,
        component_previews=[_to_workflow_step_preview_dto(c) for c in preview.component_previews],
        external_refs=preview.external_refs,
        unsupported_inline_steps=preview.unsupported_inline_steps,
        missing_external_refs=preview.missing_external_refs,
    )


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDetailDto,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Workflow not found"}},
)
async def get_workflow(
    workflow_id: uuid.UUID,
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> WorkflowDetailDto:
    workflow = await workflows_service.get_visible_workflow(workflow_id, current_user)
    favorited_ids = await _favorited_ids(favorites_service, current_user)
    return WorkflowTransformer.to_detail(workflow, str(workflow.id) in favorited_ids, current_user)


@router.get(
    "/{workflow_id}/download",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Workflow not found"}},
)
async def download(
    workflow_id: uuid.UUID,
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> Response:
    workflow = await workflows_service.get_visible_workflow(workflow_id, current_user)
    filename, content = await workflows_service.get_download(workflow)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch(
    "/steps/{step_id}",
    response_model=WorkflowStepDto,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this workflow"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Step or component not found"},
    },
)
async def update_step(
    step_id: uuid.UUID,
    dto: UpdateWorkflowStepRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> WorkflowStepDto:
    _step, workflow = await workflows_service.get_step_with_workflow(step_id)

    validator = WorkflowPermissionValidator(current_user)
    if not validator.can_update(workflow):
        logger.warning(f"User {current_user.id} not permitted to update step {step_id}")
        raise ForbiddenException("Insufficient permission to update this workflow's step")

    updated = await workflows_service.update_step_component(step_id, dto.component_id)
    logger.info(f"Updated step {step_id} -> component {dto.component_id}")
    return WorkflowTransformer.to_step(updated, current_user)


@router.post(
    "/steps/{step_id}/commands",
    response_model=WorkflowStepDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Step has no matched component to confirm"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permission for this command"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Step not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Unknown command"},
    },
)
async def execute_step_command(
    step_id: uuid.UUID,
    dto: WorkflowStepCommandExecuteRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> WorkflowStepDto:
    step, workflow = await workflows_service.get_step_with_workflow(step_id)
    command = WorkflowTransformer.to_domain_step_command(dto)

    validator = WorkflowPermissionValidator(current_user)
    if not validator.can_execute_step(workflow, command.type):
        logger.warning(f"User {current_user.id} not permitted to execute {command.type} on step {step_id}")
        raise ForbiddenException(f"Insufficient permission to execute {command.type} on this step")

    updated = await workflows_service.execute_step_command(step, command)
    logger.info(f"Executed command {command.type} on step {step_id}")
    return WorkflowTransformer.to_step(updated, current_user)


@router.post(
    "/{workflow_id}/commands",
    response_model=WorkflowDetailDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Not every step is confirmed yet"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permission for this command"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Workflow not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Unknown command"},
    },
)
async def execute_command(
    workflow_id: uuid.UUID,
    dto: WorkflowCommandExecuteRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> WorkflowDetailDto:
    workflow = await workflows_service.get_workflow(workflow_id)
    command = WorkflowTransformer.to_domain_command(dto)

    validator = WorkflowPermissionValidator(current_user)
    if not validator.can_execute(workflow, command.type):
        logger.warning(f"User {current_user.id} not permitted to execute {command.type} on workflow {workflow_id}")
        raise ForbiddenException(f"Insufficient permission to execute {command.type} on this workflow")

    updated = await workflows_service.execute_command(workflow, command, current_user.id, favorites_service)
    logger.info(f"Executed command {command.type} on workflow {workflow_id}")

    favorited_ids = await _favorited_ids(favorites_service, current_user)
    return WorkflowTransformer.to_detail(updated, str(updated.id) in favorited_ids, current_user)


@router.delete(
    "/{workflow_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this workflow"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Workflow not found"},
    },
)
async def remove(
    workflow_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> None:
    workflow = await workflows_service.get_workflow(workflow_id)

    validator = WorkflowPermissionValidator(current_user)
    if not validator.can_delete(workflow):
        logger.warning(f"User {current_user.id} not permitted to delete workflow {workflow_id}")
        raise ForbiddenException("Insufficient permission to delete this workflow")

    await favorites_service.remove_all_workflow_favorites(workflow.id)
    await workflows_service.remove(workflow)
    logger.info(f"Deleted workflow {workflow_id}")
