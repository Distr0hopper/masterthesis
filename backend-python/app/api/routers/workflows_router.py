"""/workflows - what only a workflow, the composite, has: being uploaded together with
the tools its steps run, and binding those steps to child components. Listing, reading,
publishing and deleting are shared with tools under /components."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status

from app.api.dto.common import ErrorResponse
from app.api.dto.workflow import (
    AddWorkflowVersionRequestDto,
    ComponentConfigDto,
    CreateWorkflowRequestDto,
    ParseWorkflowRequestDto,
    ParseWorkflowResponseDto,
    UpdateWorkflowStepRequestDto,
    WorkflowDetailDto,
    WorkflowStepCommandExecuteRequestDto,
    WorkflowStepDto,
)
from app.api.exception.exceptions import ForbiddenException
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.transformer.component_transformer import ComponentTransformer
from app.api.transformer.parameter_transformer import ParameterTransformer
from app.api.transformer.workflow_transformer import WorkflowTransformer
from app.application.service.auth_service import AuthService
from app.application.service.components_service import ComponentsService
from app.application.service.workflows_service import ComponentConfig, WorkflowsService
from app.domain.models.component import ComponentKind
from app.domain.models.user import User

router = APIRouter(prefix="/workflows", tags=["workflows"])
logger = logging.getLogger("app.api.routers.workflows_router")

MAX_WORKFLOW_ZIP_SIZE = 10 * 1024 * 1024


def _configs_by_step(configs: list[ComponentConfigDto]) -> dict[str, ComponentConfig]:
    return {
        c.step_id: ComponentConfig(
            step_id=c.step_id,
            reuse_component_id=c.reuse_component_id,
            new_version_of_id=c.new_version_of_id,
            name=c.name,
            domains=c.domains,
            description=c.description,
            format_labels=ParameterTransformer.to_format_labels(c.format_labels),
        )
        for c in configs
    }


def _require_size(content: bytes) -> None:
    if len(content) > MAX_WORKFLOW_ZIP_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_WORKFLOW_ZIP_SIZE} bytes)",
        )


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
            "description": "The workflow's or a configured tool's name already exists",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def create(
    dto: Annotated[CreateWorkflowRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> WorkflowDetailDto:
    if not ComponentPermissionValidator(current_user).can_create():
        raise ForbiddenException("Insufficient permission to create a workflow")

    content = await dto.file.read()
    _require_size(content)

    configs_by_step = _configs_by_step(dto.component_configs)
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
    return ComponentTransformer.to_detail(workflow, False, current_user)


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
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ParseWorkflowResponseDto:
    content = await dto.file.read()
    _require_size(content)

    parent = None
    if dto.parent_id is not None:
        parent = await components_service.get_component(dto.parent_id, ComponentKind.WORKFLOW)
        if not ComponentPermissionValidator(current_user).can_update(parent):
            raise ForbiddenException("Insufficient permission to add a version to this workflow")

    logger.info(f"Parsing workflow upload '{dto.file.filename}' for user {current_user.id}")
    preview = await workflows_service.parse_workflow_upload(content, dto.file.filename, parent, current_user.id)

    return ParseWorkflowResponseDto(
        is_zip=preview.is_zip,
        is_self_contained=preview.is_self_contained,
        workflow_name=preview.workflow_name,
        description=preview.description,
        step_count=preview.step_count,
        component_previews=[WorkflowTransformer.to_step_preview(c) for c in preview.component_previews],
        external_refs=preview.external_refs,
        inline_only_steps=preview.inline_only_steps,
        missing_external_refs=preview.missing_external_refs,
        auxiliary_files=preview.auxiliary_files,
        missing_imports=preview.missing_imports,
    )


@router.post(
    "/{workflow_id}/versions",
    response_model=WorkflowDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Invalid workflow file/archive, file too large, or a step configured wrongly",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this workflow"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Workflow not found"},
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The workflow is edited in the Workflow Builder, a configured tool's name already "
            "exists, or a step versions a tool packaged from GitHub",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def add_version(
    workflow_id: uuid.UUID,
    dto: Annotated[AddWorkflowVersionRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> WorkflowDetailDto:
    """An uploaded workflow as the next version of this one - like POST /workflows, with the
    lineage's name and domains. Its steps can also become the next version of the caller's
    tools (componentConfigs[].newVersionOfId)."""
    parent = await components_service.get_component(workflow_id, ComponentKind.WORKFLOW)
    if not ComponentPermissionValidator(current_user).can_update(parent):
        logger.warning(f"User {current_user.id} not permitted to add a version to workflow {workflow_id}")
        raise ForbiddenException("Insufficient permission to add a version to this workflow")

    content = await dto.file.read()
    _require_size(content)

    workflow = await workflows_service.add_version_from_upload(
        parent, content, dto.file.filename, dto.description, _configs_by_step(dto.component_configs), current_user.id
    )
    logger.info(f"Added version {workflow.version} to workflow '{workflow.name}' ({workflow.id})")
    favorited_names = await components_service.favorited_names(current_user)
    return ComponentTransformer.to_detail(workflow, workflow.name in favorited_names, current_user)


@router.patch(
    "/steps/{step_id}",
    response_model=WorkflowStepDto,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this workflow"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Step or component not found"},
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "The workflow is published, the step runs an inline definition, the component "
            "is deprecated, or it would make the workflow contain itself",
        },
    },
)
async def update_step(
    step_id: uuid.UUID,
    dto: UpdateWorkflowStepRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    workflows_service: Annotated[WorkflowsService, Depends(WorkflowsService.get_service)],
) -> WorkflowStepDto:
    """Bind a step to a component - a tool, or another workflow to nest."""
    _step, workflow = await workflows_service.get_step_with_workflow(step_id)

    if not ComponentPermissionValidator(current_user).can_update(workflow):
        logger.warning(f"User {current_user.id} not permitted to update step {step_id}")
        raise ForbiddenException("Insufficient permission to update this workflow's step")

    updated = await workflows_service.update_step_component(step_id, dto.component_id, current_user.id)
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
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "The workflow is published"},
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

    # ownership only - a published workflow's locked steps are the service's 409, not a 403
    if not ComponentPermissionValidator(current_user).can_update(workflow):
        logger.warning(f"User {current_user.id} not permitted to execute {command.type} on step {step_id}")
        raise ForbiddenException(f"Insufficient permission to execute {command.type} on this step")

    updated = await workflows_service.execute_step_command(step, command)
    logger.info(f"Executed command {command.type} on step {step_id}")
    return WorkflowTransformer.to_step(updated, current_user)
