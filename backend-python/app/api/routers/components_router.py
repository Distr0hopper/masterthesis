import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import Response

from app.api.dto.common import ErrorResponse, MyItemsResponseDtoV1, build_my_items_response
from app.api.dto.component import (
    AddVersionRequestDto,
    ComponentCommandExecuteRequestDto,
    ComponentDetailDto,
    ComponentListItemDto,
    ComponentPreviewDto,
    CreateComponentRequestDto,
    ExistingComponentDto,
    NameAvailabilityDto,
    PackageComponentRequestDto,
    ParseComponentRequestDto,
)
from app.api.dto.pagination import ListQueryPaginationDtoV1, PaginatedResponseDtoV1, build_paginated_response
from app.api.exception.exceptions import ForbiddenException
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.transformer.component_transformer import ComponentTransformer
from app.application.exception.favorites_exceptions import FavoritesRequireAuthError
from app.application.service.auth_service import AuthService
from app.application.service.components_service import ComponentsService
from app.application.service.favorites_service import FavoritesService
from app.domain.models.component import ComponentStatus
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.user import User
from app.domain.pagination.pagination import DEFAULT_LIMIT, MAX_LIMIT, PaginatedList
from app.domain.repository.components_repository import ComponentListFilter

router = APIRouter(prefix="/components", tags=["components"])
logger = logging.getLogger("app.api.routers.components_router")

MAX_CWL_FILE_SIZE = 1024 * 1024


async def _favorited_names(favorites_service: FavoritesService, user: User | None) -> set[str]:
    return await favorites_service.get_favorited_component_names(user.id) if user is not None else set()


@router.get("", response_model=PaginatedResponseDtoV1[ComponentListItemDto])
async def list_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    pagination_dto: Annotated[ListQueryPaginationDtoV1, Depends()],
    # repeatable: ?domain=a&domain=b selects both. json_schema_extra adds the enum purely
    # so Swagger UI renders a dropdown for each value
    domain: Annotated[list[str] | None, Query(json_schema_extra={"items": {"enum": VALID_DOMAINS}})] = None,
    favorites_only: Annotated[bool, Query(alias="favoritesOnly")] = False,
    exclude_mine: Annotated[bool, Query(alias="excludeMine")] = False,
    search: Annotated[str | None, Query()] = None,
    # off by default so the browse grid keeps its slim payload - only the workflow
    # builder, which type-checks every listed component's ports, asks for these
    include_parameters: Annotated[bool, Query(alias="includeParameters")] = False,
) -> PaginatedResponseDtoV1[ComponentListItemDto]:
    if favorites_only and current_user is None:
        raise FavoritesRequireAuthError()

    exclude_created_by = current_user.id if exclude_mine and current_user is not None else None
    favorited_by = current_user.id if favorites_only and current_user is not None else None
    pagination = pagination_dto.to_domain()
    filter = ComponentListFilter(
        domains=domain or [], exclude_created_by=exclude_created_by, favorited_by=favorited_by, search=search
    )
    components, total = await components_service.list_components(filter, pagination)
    favorited_names = await _favorited_names(favorites_service, current_user)

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
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    published_offset: Annotated[int, Query(alias="publishedOffset", ge=0)] = 0,
    unpublished_offset: Annotated[int, Query(alias="unpublishedOffset", ge=0)] = 0,
) -> MyItemsResponseDtoV1[ComponentListItemDto]:
    published_pagination = PaginatedList(limit=limit, offset=published_offset)
    unpublished_pagination = PaginatedList(limit=limit, offset=unpublished_offset)

    published_components, published_total = await components_service.list_my_components_by_status(
        current_user.id, ComponentStatus.PUBLISHED, published_pagination
    )
    unpublished_components, unpublished_total = await components_service.list_my_components_by_status(
        current_user.id, ComponentStatus.DRAFT, unpublished_pagination
    )
    favorited_names = await _favorited_names(favorites_service, current_user)

    def to_items(components: list) -> list[ComponentListItemDto]:
        return [ComponentTransformer.to_list_item(c, c.name in favorited_names, current_user) for c in components]

    return build_my_items_response(
        (to_items(published_components), published_total),
        published_pagination,
        (to_items(unpublished_components), unpublished_total),
        unpublished_pagination,
    )


@router.get("/latest", response_model=list[ComponentListItemDto])
async def list_latest_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    limit: int = 6,
) -> list[ComponentListItemDto]:
    components = await components_service.get_latest_components(limit)
    favorited_names = await _favorited_names(favorites_service, current_user)
    return [ComponentTransformer.to_list_item(c, c.name in favorited_names, current_user) for c in components]


@router.post(
    "/parse",
    response_model=ComponentPreviewDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid CWL or file too large"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
    },
)
async def parse_component(
    dto: Annotated[ParseComponentRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ComponentPreviewDto:
    """Read an uploaded .cwl without persisting it, so the user can review the component
    before creating it. Mirrors POST /workflows/parse."""
    content = await dto.cwl_file.read()
    if len(content) > MAX_CWL_FILE_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_CWL_FILE_SIZE} bytes)",
        )

    logger.info(f"Parsing component upload '{dto.cwl_file.filename}' for user {current_user.id}")
    parsed = components_service.parse_cwl(content)
    return ComponentPreviewDto(
        cwl_content=parsed.cwl_content,
        cwl_type=parsed.cwl_type,
        description=parsed.description,
        dockerfile_content=parsed.dockerfile_content,
        docker_pull_reference=parsed.docker_pull_reference,
        parameters=[
            ComponentTransformer.to_preview_parameter(p, "preview") for p in parsed.parameters
        ],
    )


@router.get("/name-availability", response_model=NameAvailabilityDto)
async def check_name_availability(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    name: Annotated[str, Query(min_length=1)],
) -> NameAvailabilityDto:
    """Whether `name` is still free for a new component lineage.

    NOTE: must stay declared above GET /{component_id} - FastAPI matches routes in
    declaration order, and "name-availability" would otherwise be parsed as a component id.
    """
    existing = await components_service.find_latest_version_by_name(name)
    return NameAvailabilityDto(
        name=name,
        available=existing is None,
        existing=None
        if existing is None
        else ExistingComponentDto(
            id=existing.id,
            name=existing.name,
            version=existing.version,
            domains=ComponentTransformer.to_domains(existing),
            status=existing.status,
        ),
    )


@router.post(
    "",
    response_model=ComponentDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid CWL content or file too large"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "A component with this name already exists"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def create(
    dto: Annotated[CreateComponentRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ComponentDetailDto:
    validator = ComponentPermissionValidator(current_user)
    if not validator.can_create():
        raise ForbiddenException("Insufficient permission to create a component")

    content = await dto.cwl_file.read()
    if len(content) > MAX_CWL_FILE_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_CWL_FILE_SIZE} bytes)",
        )

    logger.info(f"Creating component '{dto.name}' for user {current_user.id}")
    component = ComponentTransformer.from_create_dto(dto, content.decode("utf-8"), current_user.id)
    created = await components_service.create_manual(component)
    logger.info(f"Created component {created.id} ('{created.name}' v{created.version})")
    return ComponentTransformer.to_detail(created, is_favorite=False, current_user=current_user)


@router.post(
    "/package",
    response_model=ComponentDetailDto,
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
            "description": "This exact commit is already packaged, or the derived name collides with an existing component",
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def package(
    dto: PackageComponentRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> ComponentDetailDto:
    existing = await components_service.find_component_by_repo_url(dto.repo_url)
    logger.info(f"Packaging component from {dto.repo_url}")

    if existing is not None:
        validator = ComponentPermissionValidator(current_user)
        if not validator.can_update(existing):
            logger.warning(f"User {current_user.id} not permitted to package a new version of repo {dto.repo_url}")
            raise ForbiddenException("Insufficient permission to package a new version of this component")
        component = await components_service.package_next_version(existing, dto.description)
    else:
        component = await components_service.create_from_url(dto.repo_url, dto.domains, dto.description, current_user.id)

    logger.info(f"Packaging complete: '{component.name}' v{component.version} ({component.id})")
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(component, component.name in favorited_names, current_user)


@router.post(
    "/{component_id}/versions",
    response_model=ComponentDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Invalid CWL content or file too large"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this component"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
    },
)
async def add_version(
    component_id: uuid.UUID,
    dto: Annotated[AddVersionRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> ComponentDetailDto:
    parent = await components_service.get_component(component_id)

    validator = ComponentPermissionValidator(current_user)
    if not validator.can_update(parent):
        logger.warning(f"User {current_user.id} not permitted to add version to component {component_id}")
        raise ForbiddenException("Insufficient permission to add a version to this component")

    content = await dto.cwl_file.read()
    if len(content) > MAX_CWL_FILE_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_CWL_FILE_SIZE} bytes)",
        )

    draft = ComponentTransformer.from_add_version_dto(parent, dto, content.decode("utf-8"))
    component = await components_service.add_manual_version(draft)
    logger.info(f"Added version {component.version} to component '{parent.name}' ({component.id})")
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(component, component.name in favorited_names, current_user)


@router.get(
    "/{component_id}",
    response_model=ComponentDetailDto,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def get_component(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> ComponentDetailDto:
    component = await components_service.get_visible_component(component_id, current_user)
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(component, component.name in favorited_names, current_user)


@router.get(
    "/{component_id}/versions",
    response_model=list[ComponentListItemDto],
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def get_versions(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> list[ComponentListItemDto]:
    component = await components_service.get_visible_component(component_id, current_user)
    versions = await components_service.get_visible_versions(component, current_user)
    favorited_names = await _favorited_names(favorites_service, current_user)
    return [ComponentTransformer.to_list_item(v, v.name in favorited_names, current_user) for v in versions]


@router.get(
    "/{component_id}/download",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def download(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> Response:
    component = await components_service.get_visible_component(component_id, current_user)
    filename, content = await components_service.get_cwl_download(component)
    return Response(
        content=content,
        media_type="application/yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post(
    "/{component_id}/commands",
    response_model=ComponentDetailDto,
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "model": ErrorResponse,
            "description": "Command is missing a payload field it requires (e.g. UPDATE_DOMAIN without domains)",
        },
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Insufficient permission for this command"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Unknown command"},
    },
)
async def execute_command(
    component_id: uuid.UUID,
    dto: ComponentCommandExecuteRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> ComponentDetailDto:
    component = await components_service.get_visible_component(component_id, current_user)
    command = ComponentTransformer.to_domain_command(dto)

    validator = ComponentPermissionValidator(current_user)
    if not validator.can_execute(component, command.type):
        logger.warning(f"User {current_user.id} not permitted to execute {command.type} on component {component_id}")
        raise ForbiddenException(f"Insufficient permission to execute {command.type} on this component")

    updated = await components_service.execute_command(component, command, current_user.id, favorites_service)
    logger.info(f"Executed command {command.type} on component {component_id}")
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(updated, updated.name in favorited_names, current_user)


@router.delete(
    "/{component_id}",
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this component"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
    },
)
async def remove(
    component_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> None:
    component = await components_service.get_component(component_id)

    validator = ComponentPermissionValidator(current_user)
    if not validator.can_delete(component):
        logger.warning(f"User {current_user.id} not permitted to delete component {component_id}")
        raise ForbiddenException("Insufficient permission to delete this component")

    versions = await components_service.get_versions(component)
    await components_service.remove(component)
    logger.info(f"Deleted component {component_id}")

    if len(versions) == 1:
        await favorites_service.remove_all_favorites(component.name)


@router.get(
    "/{component_id}/bundle",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def bundle(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
) -> Response:
    component = await components_service.get_visible_component(component_id, current_user)
    filename, content = await components_service.get_bundle(component)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )