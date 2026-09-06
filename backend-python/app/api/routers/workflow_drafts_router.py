import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from app.api.dto.common import ErrorResponse
from app.api.dto.workflow_draft import (
    PublishedWorkflowDto,
    WorkflowDraftDetailDto,
    WorkflowDraftListItemDto,
    WorkflowDraftWriteRequestDto,
)
from app.api.transformer.workflow_draft_transformer import WorkflowDraftTransformer
from app.application.service.auth_service import AuthService
from app.application.service.workflow_draft_service import WorkflowDraftService
from app.domain.models.user import User

router = APIRouter(prefix="/workflow-drafts", tags=["workflow-drafts"])
logger = logging.getLogger("app.api.routers.workflow_drafts_router")

# every route here is owner-scoped, so 401 is always possible
_OWNED_RESPONSES = {
    status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
    status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the owner of this draft"},
    status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Draft does not exist"},
}


@router.get("", response_model=list[WorkflowDraftListItemDto])
async def list_my_drafts(
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> list[WorkflowDraftListItemDto]:
    drafts = await service.list_my_drafts(current_user.id)
    return [WorkflowDraftTransformer.to_list_item(d) for d in drafts]


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
    draft = await service.create_draft(
        name=dto.name,
        canvas_state=dto.canvas_state,
        node_count=dto.node_count,
        user_id=current_user.id,
    )
    logger.info(f"Created workflow draft {draft.id} for user {current_user.id}")
    return WorkflowDraftTransformer.to_detail(draft)


@router.get("/{draft_id}", response_model=WorkflowDraftDetailDto, responses=_OWNED_RESPONSES)
async def get_draft(
    draft_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> WorkflowDraftDetailDto:
    # not-found/forbidden surface through the registered exception handlers, matching
    # every other router here - no try/except at the endpoint
    draft = await service.get_draft(draft_id, current_user.id)
    return WorkflowDraftTransformer.to_detail(draft)


@router.put("/{draft_id}", response_model=WorkflowDraftDetailDto, responses=_OWNED_RESPONSES)
async def update_draft(
    draft_id: uuid.UUID,
    dto: WorkflowDraftWriteRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> WorkflowDraftDetailDto:
    draft = await service.get_draft(draft_id, current_user.id)
    updated = await service.update_draft(
        draft=draft,
        name=dto.name,
        canvas_state=dto.canvas_state,
        node_count=dto.node_count,
    )
    logger.info(f"Updated workflow draft {draft_id}")
    return WorkflowDraftTransformer.to_detail(updated)


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT, responses=_OWNED_RESPONSES)
async def delete_draft(
    draft_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> Response:
    draft = await service.get_draft(draft_id, current_user.id)
    await service.delete_draft(draft)
    logger.info(f"Deleted workflow draft {draft_id}")
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
    """Main Workflow CWL plus one file per step, as a zip.

    Not-found/forbidden/export-validation all surface through the registered exception
    handlers, matching every other endpoint here.
    """
    draft = await service.get_draft(draft_id, current_user.id)
    filename, zip_bytes = await service.export_to_zip(draft)

    logger.info(f"Exported workflow draft {draft_id} as '{filename}'")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            # the browser fetch reads the filename off this header, which is not exposed
            # cross-origin by default (the SPA runs on a different port than the API)
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


@router.post(
    "/{draft_id}/publish",
    response_model=PublishedWorkflowDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        **_OWNED_RESPONSES,
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Canvas cannot be published"},
    },
)
async def publish_draft(
    draft_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    service: Annotated[WorkflowDraftService, Depends(WorkflowDraftService.get_service)],
) -> PublishedWorkflowDto:
    """Record the draft as a Workflow. Separate from export, which only downloads."""
    draft = await service.get_draft(draft_id, current_user.id)
    workflow = await service.publish(draft, current_user.id)

    logger.info(f"Published workflow draft {draft_id} as workflow {workflow.id}")
    return PublishedWorkflowDto(
        workflow_id=workflow.id,
        name=workflow.name,
        step_count=len(workflow.steps),
    )
