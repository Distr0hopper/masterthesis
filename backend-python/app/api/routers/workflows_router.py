import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import Response

from app.api.dto.common import ErrorResponse
from app.api.dto.workflow import (
    CreateWorkflowRequestDto,
    UpdateWorkflowStepRequestDto,
    WorkflowDetailDto,
    WorkflowListItemDto,
    WorkflowStepDto,
)
from app.api.exception.exceptions import ForbiddenException
from app.api.permission.workflow_permission_validator import WorkflowPermissionValidator
from app.api.transformer.workflow_transformer import WorkflowTransformer
from app.application.service.auth_service import AuthService
from app.application.service.workflows_service import WorkflowsService
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.user import User

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger("app.api.routers.workflows_router")

MAX_WORKFLOW_ZIP_SIZE = 10 * 1024 * 1024


@router.get("", response_model=list[WorkflowListItemDto])
async def list_workflows(
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    domain: Annotated[str | None, Query(json_schema_extra={"enum": VALID_DOMAINS})] = None,
) -> list[WorkflowListItemDto]:
    workflows = await workflows_service.list_workflows(domain)
    return [WorkflowTransformer.to_list_item(w) for w in workflows]


@router.get(
    "/mine",
    response_model=list[WorkflowListItemDto],
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"}},
)
async def list_my_workflows(
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> list[WorkflowListItemDto]:
    workflows = await workflows_service.list_my_workflows(current_user.id)
    return [WorkflowTransformer.to_list_item(w) for w in workflows]


@router.post(
    "",
    response_model=WorkflowDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid zip archive or file too large"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
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

    content = await dto.zip_file.read()
    if len(content) > MAX_WORKFLOW_ZIP_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_WORKFLOW_ZIP_SIZE} bytes)",
        )

    logger.info(f"Creating workflow '{dto.name}' for user {current_user.id}")
    workflow = await workflows_service.create_from_zip(content, dto.name, dto.description, dto.domains, current_user.id)
    logger.info(f"Created workflow {workflow.id} ('{workflow.name}') with {len(workflow.steps)} steps")
    return WorkflowTransformer.to_detail(workflow)


@router.get(
    "/{workflow_id}",
    response_model=WorkflowDetailDto,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Workflow not found"}},
)
async def get_workflow(
    workflow_id: uuid.UUID,
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> WorkflowDetailDto:
    workflow = await workflows_service.get_visible_workflow(workflow_id, current_user)
    return WorkflowTransformer.to_detail(workflow)


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
    return WorkflowTransformer.to_step(updated)


@router.post(
    "/steps/{step_id}/confirm",
    response_model=WorkflowStepDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Step has no matched component to confirm"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this workflow"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Step not found"},
    },
)
async def confirm_step(
    step_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> WorkflowStepDto:
    _step, workflow = await workflows_service.get_step_with_workflow(step_id)

    validator = WorkflowPermissionValidator(current_user)
    if not validator.can_update(workflow):
        logger.warning(f"User {current_user.id} not permitted to confirm step {step_id}")
        raise ForbiddenException("Insufficient permission to confirm this workflow's step")

    confirmed = await workflows_service.confirm_step(step_id)
    logger.info(f"Confirmed step {step_id}")
    return WorkflowTransformer.to_step(confirmed)


@router.post(
    "/{workflow_id}/publish",
    response_model=WorkflowDetailDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Not every step is confirmed yet"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this workflow"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Workflow not found"},
    },
)
async def publish(
    workflow_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> WorkflowDetailDto:
    workflow = await workflows_service.get_workflow(workflow_id)

    validator = WorkflowPermissionValidator(current_user)
    if not validator.can_update(workflow):
        logger.warning(f"User {current_user.id} not permitted to publish workflow {workflow_id}")
        raise ForbiddenException("Insufficient permission to publish this workflow")

    published = await workflows_service.publish(workflow)
    logger.info(f"Published workflow {workflow_id}")
    return WorkflowTransformer.to_detail(published)


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
) -> None:
    workflow = await workflows_service.get_workflow(workflow_id)

    validator = WorkflowPermissionValidator(current_user)
    if not validator.can_delete(workflow):
        logger.warning(f"User {current_user.id} not permitted to delete workflow {workflow_id}")
        raise ForbiddenException("Insufficient permission to delete this workflow")

    await workflows_service.remove(workflow)
    logger.info(f"Deleted workflow {workflow_id}")
