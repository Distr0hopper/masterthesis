import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.dto.common import ErrorResponse
from app.api.dto.workflow_draft import (
    SyncedWorkflowDto,
    WorkflowDraftDetailDto,
    WorkflowDraftListItemDto,
    WorkflowDraftWriteRequestDto,
)
from app.api.exception.exceptions import ForbiddenException
from app.api.permission.workflow_draft_permission_validator import WorkflowDraftPermissionValidator
from app.api.transformer.workflow_draft_transformer import WorkflowDraftTransformer
from app.application.exception.workflow_draft_exceptions import WorkflowDraftNotFoundError
from app.application.service.auth_service import AuthService
from app.application.service.workflow_draft_service import WorkflowDraftService
from app.domain.models.user import User
from app.domain.models.workflow_draft import WorkflowDraft

router = APIRouter(prefix="/workflow-drafts", tags=["workflow-drafts"])
logger = logging.getLogger("app.api.routers.workflow_drafts_router")

_OWNED_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
    # a canvas is its owner's alone - for anyone else it does not exist, so no 403
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Draft does not exist, or is not yours"},
}


async def _readable_draft(draft_id: uuid.UUID, user: User, service: WorkflowDraftService) -> WorkflowDraft:
    """A draft the caller may not read does not exist for them - 404, never a 403 that
    would confirm another user's canvas sits behind this id."""
    draft = await service.get_draft(draft_id)
    if not WorkflowDraftPermissionValidator(user).can_read(draft):
        raise WorkflowDraftNotFoundError(draft_id)
    return draft


async def _to_detail(draft: WorkflowDraft, service: WorkflowDraftService) -> WorkflowDraftDetailDto:
    """Every response that replaces the client's cached draft carries what the canvas is
    linked to and which of its components are gone - the builder reads both off it."""
    linked = await service.linked_workflows({draft.id})
    return WorkflowDraftTransformer.to_detail(
        draft, linked.get(draft.id), missing_component_ids=await service.missing_component_ids(draft)
    )


@router.get("", response_model=list[WorkflowDraftListItemDto])
async def list_my_drafts(
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> list[WorkflowDraftListItemDto]:
    drafts = await service.list_my_drafts(current_user.id)
    linked = await service.linked_workflows({d.id for d in drafts})
    return [WorkflowDraftTransformer.to_list_item(d, linked.get(d.id)) for d in drafts]


@router.post(
    "",
    response_model=WorkflowDraftDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def create_draft(
    dto: WorkflowDraftWriteRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> WorkflowDraftDetailDto:
    if not WorkflowDraftPermissionValidator(current_user).can_create():
        raise ForbiddenException("Insufficient permission to create a workflow draft")

    draft = await service.create_draft(
        name=dto.name,
        canvas_state=dto.canvas_state,
        node_count=dto.node_count,
        user_id=current_user.id,
    )
    logger.info(f"Created workflow draft {draft.id} for user {current_user.id}")
    return await _to_detail(draft, service)


@router.get("/{draft_id}", response_model=WorkflowDraftDetailDto, responses=_OWNED_RESPONSES)
async def get_draft(
    draft_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> WorkflowDraftDetailDto:
    draft = await _readable_draft(draft_id, current_user, service)

    return await _to_detail(draft, service)


@router.put("/{draft_id}", response_model=WorkflowDraftDetailDto, responses=_OWNED_RESPONSES)
async def update_draft(
    draft_id: uuid.UUID,
    dto: WorkflowDraftWriteRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> WorkflowDraftDetailDto:
    draft = await _readable_draft(draft_id, current_user, service)
    if not WorkflowDraftPermissionValidator(current_user).can_update(draft):
        raise ForbiddenException("Insufficient permission to update this workflow draft")

    updated = await service.update_draft(
        draft=draft,
        name=dto.name,
        canvas_state=dto.canvas_state,
        node_count=dto.node_count,
    )
    logger.info(f"Updated workflow draft {draft_id}")
    return await _to_detail(updated, service)


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_OWNED_RESPONSES)
async def delete_draft(
    draft_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
    # opt-in: also delete the Workflow this draft was synced to in My Components
    delete_linked_workflow: Annotated[bool, Query(alias="deleteLinkedWorkflow")] = False,
) -> Response:
    draft = await _readable_draft(draft_id, current_user, service)
    if not WorkflowDraftPermissionValidator(current_user).can_delete(draft):
        raise ForbiddenException("Insufficient permission to delete this workflow draft")

    await service.delete_draft(draft, delete_linked_workflow)
    logger.info(f"Deleted workflow draft {draft_id}{' and its linked workflow' if delete_linked_workflow else ''}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{draft_id}/export",
    response_class=Response,
    responses={
        **_OWNED_RESPONSES,
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Canvas cannot be exported"},
        status.HTTP_200_OK: {"content": {"application/zip": {}}, "description": "CWL archive"},
    },
)
async def export_draft(
    draft_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> Response:
    draft = await _readable_draft(draft_id, current_user, service)

    filename, zip_bytes = await service.export_to_zip(draft)

    logger.info(f"Exported workflow draft {draft_id} as '{filename}'")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/{draft_id}/export/inputs",
    response_class=Response,
    responses={
        **_OWNED_RESPONSES,
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Canvas cannot be exported"},
        status.HTTP_200_OK: {"content": {"application/yaml": {}}, "description": "CWL job file (inputs.yaml)"},
    },
)
async def export_draft_inputs(
    draft_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> Response:
    """The inputs.yaml for the workflow /export produces: one placeholder per workflow input."""
    draft = await _readable_draft(draft_id, current_user, service)

    filename, inputs_yaml = await service.export_inputs_yaml(draft)

    logger.info(f"Exported inputs of workflow draft {draft_id} as '{filename}'")
    return Response(
        content=inputs_yaml,
        media_type="application/yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{draft_id}/sync",
    response_model=SyncedWorkflowDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        **_OWNED_RESPONSES,
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Canvas cannot be synced"},
    },
)
async def sync_draft_to_my_components(
    draft_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> SyncedWorkflowDto:
    """Mirror the draft into My Components as a Workflow row. Idempotent per draft."""
    draft = await _readable_draft(draft_id, current_user, service)
    if not WorkflowDraftPermissionValidator(current_user).can_update(draft):
        raise ForbiddenException("Insufficient permission to sync this workflow draft")

    workflow = await service.sync_to_my_components(draft)

    logger.info(f"Synced workflow draft {draft_id} into My Components as workflow {workflow.id}")
    return WorkflowDraftTransformer.to_synced(workflow)
