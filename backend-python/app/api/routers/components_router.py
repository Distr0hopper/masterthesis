"""/components - the composite's uniform API: every operation that works the same for a
tool and a workflow. Kind-specific operations live under /tools and /workflows."""

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response

from app.api.dto.common import ErrorResponse, MyItemsResponseDtoV1, build_my_items_response
from app.api.dto.component import (
    ComponentCommandExecuteRequestDto,
    ComponentImpactDto,
    ComponentUsageDto,
    NameAvailabilityDto,
)
from app.api.dto.component_variants import ComponentDetailDto, ComponentListItemDto
from app.api.dto.pagination import ListQueryPaginationDtoV1, PaginatedResponseDtoV1, build_paginated_response
from app.api.exception.exceptions import ForbiddenException
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.transformer.component_transformer import ComponentTransformer
from app.application.exception.favorites_exceptions import FavoritesRequireAuthError
from app.application.service.auth_service import AuthService
from app.application.service.compatibility_service import CompatibilityService
from app.application.service.components_service import ComponentsService
from app.domain.models.component import ComponentKind, ComponentStatus
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.user import User
from app.domain.pagination.pagination import DEFAULT_LIMIT, MAX_LIMIT, PaginatedList
from app.domain.repository.components_repository import ComponentListFilter

router = APIRouter(prefix="/components", tags=["components"])
logger = logging.getLogger("app.api.routers.components_router")


@router.get("", response_model=PaginatedResponseDtoV1[ComponentListItemDto])
async def list_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    compatibility_service: Annotated[CompatibilityService, Depends(CompatibilityService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    pagination_dto: Annotated[ListQueryPaginationDtoV1, Depends()],
    # omitted lists both kinds - tools and workflows side by side
    kind: Annotated[ComponentKind | None, Query()] = None,
    # repeatable: ?domain=a&domain=b selects both. json_schema_extra adds the enum purely
    # so Swagger UI renders a dropdown for each value
    domain: Annotated[list[str] | None, Query(json_schema_extra={"items": {"enum": VALID_DOMAINS}})] = None,
    favorites_only: Annotated[bool, Query(alias="favoritesOnly")] = False,
    exclude_mine: Annotated[bool, Query(alias="excludeMine")] = False,
    search: Annotated[str | None, Query()] = None,
    # off by default so the browse grid keeps its slim payload - only the workflow
    # builder, which type-checks every listed component's ports, asks for these
    include_parameters: Annotated[bool, Query(alias="includeParameters")] = False,
    # repeatable: the component of every workflow-builder canvas node, most recently added
    # first. Switches the list to the builder palette's order - ranked by how well each
    # component fits the canvas, before paging - and implies includeParameters
    rank_against: Annotated[list[uuid.UUID] | None, Query(alias="rankAgainst")] = None,
    favorites_first: Annotated[bool, Query(alias="favoritesFirst")] = False,
) -> PaginatedResponseDtoV1[ComponentListItemDto]:
    if favorites_only and current_user is None:
        raise FavoritesRequireAuthError()

    exclude_created_by = current_user.id if exclude_mine and current_user is not None else None
    favorited_by = current_user.id if favorites_only and current_user is not None else None
    pagination = pagination_dto.to_domain()
    filter = ComponentListFilter(
        kind=kind,
        domains=domain or [],
        exclude_created_by=exclude_created_by,
        favorited_by=favorited_by,
        search=search,
        favorites_first_for=current_user.id if favorites_first and current_user is not None else None,
    )
    favorited_names = await components_service.favorited_names(current_user)

    if rank_against is not None:
        candidates = await components_service.list_all_components(filter)
        ranked, total = await compatibility_service.rank_components(
            candidates, rank_against, favorited_names, current_user, pagination
        )
        ranked_items = [
            ComponentTransformer.to_ranked_list_item(r, r.component.name in favorited_names, current_user)
            for r in ranked
        ]
        return build_paginated_response(ranked_items, total, pagination)

    components, total = await components_service.list_components(filter, pagination)
    items = [
        ComponentTransformer.to_list_item(c, c.name in favorited_names, current_user, include_parameters)
        for c in components
    ]
    return build_paginated_response(items, total, pagination)


@router.get(
    "/mine",
    response_model=MyItemsResponseDtoV1[ComponentListItemDto],
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"}},
)
async def list_my_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    kind: Annotated[ComponentKind | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    published_offset: Annotated[int, Query(alias="publishedOffset", ge=0)] = 0,
    unpublished_offset: Annotated[int, Query(alias="unpublishedOffset", ge=0)] = 0,
) -> MyItemsResponseDtoV1[ComponentListItemDto]:
    published_pagination = PaginatedList(limit=limit, offset=published_offset)
    unpublished_pagination = PaginatedList(limit=limit, offset=unpublished_offset)

    published, published_total = await components_service.list_my_components_by_status(
        current_user.id, ComponentStatus.PUBLISHED, kind, published_pagination
    )
    unpublished, unpublished_total = await components_service.list_my_components_by_status(
        current_user.id, ComponentStatus.DRAFT, kind, unpublished_pagination
    )
    favorited_names = await components_service.favorited_names(current_user)

    def to_items(components: list) -> list:
        return [ComponentTransformer.to_list_item(c, c.name in favorited_names, current_user) for c in components]

    return build_my_items_response(
        (to_items(published), published_total),
        published_pagination,
        (to_items(unpublished), unpublished_total),
        unpublished_pagination,
    )


@router.get("/latest", response_model=list[ComponentListItemDto])
async def list_latest_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    kind: Annotated[ComponentKind | None, Query()] = None,
    limit: int = 6,
) -> list[ComponentListItemDto]:
    components = await components_service.get_latest_components(limit, kind)
    favorited_names = await components_service.favorited_names(current_user)
    return [ComponentTransformer.to_list_item(c, c.name in favorited_names, current_user) for c in components]


@router.get("/name-availability", response_model=NameAvailabilityDto)
async def check_name_availability(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    name: Annotated[str, Query(min_length=1)],
    # a component trivially holds its own name - a rename check leaves its lineage out
    exclude_id: Annotated[uuid.UUID | None, Query(alias="excludeId")] = None,
) -> NameAvailabilityDto:
    """Whether `name` is still free for a new lineage - of either kind.

    `available` reflects the whole catalogue, since names are globally unique across tools
    and workflows. `existing` is only filled in when the caller may actually see that
    component - a name held by somebody else's draft still reads as taken, just without
    details.

    NOTE: must stay declared above GET /{component_id} - FastAPI matches routes in
    declaration order, and "name-availability" would otherwise be parsed as a component id.
    """
    taken = await components_service.find_latest_version_by_name(name, exclude_id) is not None
    existing = await components_service.find_visible_latest_version_by_name(name, current_user, exclude_id)
    return NameAvailabilityDto(
        name=name,
        available=not taken,
        existing=None if existing is None else ComponentTransformer.to_existing(existing, current_user),
    )


@router.get(
    "/{component_id}",
    response_model=ComponentDetailDto,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def get_component(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> ComponentDetailDto:
    component = await components_service.get_visible_component(component_id, current_user)
    favorited_names = await components_service.favorited_names(current_user)
    return ComponentTransformer.to_detail(component, component.name in favorited_names, current_user)


@router.get(
    "/{component_id}/versions",
    response_model=list[ComponentListItemDto],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def get_versions(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> list[ComponentListItemDto]:
    component = await components_service.get_visible_component(component_id, current_user)
    versions = await components_service.get_visible_versions(component, current_user)
    favorited_names = await components_service.favorited_names(current_user)
    return [ComponentTransformer.to_list_item(v, v.name in favorited_names, current_user) for v in versions]


@router.get(
    "/{component_id}/usages",
    response_model=list[ComponentUsageDto],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def get_usages(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> list[ComponentUsageDto]:
    """The workflows running any version of this component - a tool, or a nested
    workflow - only those the caller may see."""
    component = await components_service.get_visible_component(component_id, current_user)
    usages = await components_service.list_usages(component, current_user)
    return [ComponentTransformer.to_usage(u) for u in usages]


@router.get(
    "/{component_id}/impact",
    response_model=ComponentImpactDto,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this component"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
    },
)
async def get_impact(
    component_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ComponentImpactDto:
    """What unpublishing or deleting exactly this version touches - read by both dialogs
    beforehand: the public workflows above it (other users' ones block either action), and
    the workflows and builder drafts a delete unmatches."""
    component = await components_service.get_component(component_id)
    if not ComponentPermissionValidator(current_user).can_update(component):
        raise ForbiddenException("Insufficient permission to unpublish or delete this component")

    impact = await components_service.get_impact(component, current_user)
    return ComponentTransformer.to_impact(impact)


@router.get(
    "/{component_id}/download",
    responses={
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Two documents of the workflow's tree need the same file name",
        },
    },
)
async def download(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> Response:
    """A tool as its .cwl document; a workflow as a zip of its whole tree."""
    component = await components_service.get_visible_component(component_id, current_user)
    file = await components_service.get_download(component)
    return Response(
        content=file.content,
        media_type=file.media_type,
        headers={"Content-Disposition": f'attachment; filename="{file.filename}"'},
    )


@router.post(
    "/{component_id}/commands",
    response_model=ComponentDetailDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Command is missing a payload field it requires (e.g. UPDATE_DOMAIN without domains), "
            "or a workflow is not ready to publish",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permission for this command"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "PUBLISH of a workflow that still runs draft components, or UNPUBLISH of a version "
            "that public workflows run (other users' ones, or your own without unpublishParents)",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Unknown command"},
    },
)
async def execute_command(
    component_id: uuid.UUID,
    dto: ComponentCommandExecuteRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ComponentDetailDto:
    component = await components_service.get_visible_component(component_id, current_user)
    command = ComponentTransformer.to_domain_command(dto)

    validator = ComponentPermissionValidator(current_user)
    if not validator.can_execute(component, command.type):
        logger.warning(f"User {current_user.id} not permitted to execute {command.type} on component {component_id}")
        raise ForbiddenException(f"Insufficient permission to execute {command.type} on this component")

    updated = await components_service.execute_command(component, command, current_user.id)
    logger.info(f"Executed command {command.type} on {ComponentKind(updated.kind).value} {component_id}")
    favorited_names = await components_service.favorited_names(current_user)
    return ComponentTransformer.to_detail(updated, updated.name in favorited_names, current_user)


@router.delete(
    "/{component_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this component"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
        status.HTTP_409_CONFLICT: {
            "model": ErrorResponse,
            "description": "Public workflows run this version - other users' ones, or your own without "
            "unpublishParents",
        },
    },
)
async def remove(
    component_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    # workflows only: also delete the builder draft this workflow was synced from
    delete_linked_draft: Annotated[bool, Query(alias="deleteLinkedDraft")] = False,
    # also unpublish your own public workflows that run this version, at any depth
    unpublish_parents: Annotated[bool, Query(alias="unpublishParents")] = False,
) -> None:
    component = await components_service.get_component(component_id)

    validator = ComponentPermissionValidator(current_user)
    if not validator.can_delete(component):
        logger.warning(f"User {current_user.id} not permitted to delete component {component_id}")
        raise ForbiddenException("Insufficient permission to delete this component")

    kind = ComponentKind(component.kind).value
    deleted_draft = await components_service.remove(
        component, current_user.id, delete_linked_draft, unpublish_parents
    )
    logger.info(f"Deleted {kind} {component_id}{' and its builder draft' if deleted_draft else ''}")
