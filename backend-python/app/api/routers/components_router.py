import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import Response

from app.api.dto.common import ErrorResponse
from app.api.dto.component import (
    AddVersionRequestDto,
    ComponentDetailDto,
    ComponentListItemDto,
    CreateComponentRequestDto,
    PackageComponentRequestDto,
    UpdateComponentRequestDto,
)
from app.api.exception.exceptions import ForbiddenException
from app.api.permission.component_permission_validator import ComponentPermissionValidator
from app.api.transformer.component_transformer import ComponentTransformer
from app.application.exception.favorites_exceptions import FavoritesRequireAuthError
from app.application.service.auth_service import AuthService
from app.application.service.components_service import ComponentsService
from app.application.service.favorites_service import FavoritesService
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.user import User

router = APIRouter(prefix="/components", tags=["components"])
logger = logging.getLogger("app.api.routers.components_router")

MAX_CWL_FILE_SIZE = 1024 * 1024


async def _favorited_names(favorites_service: FavoritesService, user: User | None) -> set[str]:
    return await favorites_service.get_favorited_component_names(user.id) if user is not None else set()


@router.get("", response_model=list[ComponentListItemDto])
async def list_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    # json_schema_extra adds the enum purely so Swagger UI renders a dropdown
    domain: Annotated[str | None, Query(json_schema_extra={"enum": VALID_DOMAINS})] = None,
    favorites_only: Annotated[bool, Query(alias="favoritesOnly")] = False,
    exclude_mine: Annotated[bool, Query(alias="excludeMine")] = False,
) -> list[ComponentListItemDto]:
    if favorites_only and current_user is None:
        raise FavoritesRequireAuthError()

    # unlike favoritesOnly, excludeMine has a sensible no-op meaning for anonymous
    # visitors (there's no "mine" to exclude), so no auth error here
    exclude_created_by = current_user.id if exclude_mine and current_user is not None else None
    components = await components_service.list_components(domain, exclude_created_by)
    favorited_names = await _favorited_names(favorites_service, current_user)

    if favorites_only:
        components = [c for c in components if c.name in favorited_names]

    return [ComponentTransformer.to_list_item(c, c.name in favorited_names) for c in components]


@router.get("/mine", response_model=list[ComponentListItemDto])
async def list_my_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
) -> list[ComponentListItemDto]:
    components = await components_service.list_my_components(current_user.id)
    favorited_names = await _favorited_names(favorites_service, current_user)
    return [ComponentTransformer.to_list_item(c, c.name in favorited_names) for c in components]


@router.get("/latest", response_model=list[ComponentListItemDto])
async def list_latest_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
    current_user: Annotated[User | None, Depends(AuthService.get_current_user_optional)],
    limit: int = 6,
) -> list[ComponentListItemDto]:
    components = await components_service.get_latest_components(limit)
    favorited_names = await _favorited_names(favorites_service, current_user)
    return [ComponentTransformer.to_list_item(c, c.name in favorited_names) for c in components]


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
    # brand-new component row, cannot already exist in favorites (FK requires the row first)
    return ComponentTransformer.to_detail(created, is_favorite=False)


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
        component = await components_service.create_from_url(dto.repo_url, dto.domain, dto.description, current_user.id)

    logger.info(f"Packaging complete: '{component.name}' v{component.version} ({component.id})")
    # a new version shares its lineage's name with prior versions, so it may already be
    # favorited (by this or any other user) - not guaranteed False like a brand-new lineage
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(component, component.name in favorited_names)


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
    # shares the parent's name/lineage, so it may already be favorited
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(component, component.name in favorited_names)


@router.post(
    "/{component_id}/versions/package",
    response_model=ComponentDetailDto,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": ErrorResponse, "description": "Component has no repoUrl or packaging failed"},
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this component"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
        status.HTTP_409_CONFLICT: {"model": ErrorResponse, "description": "This exact commit is already packaged"},
    },
)
async def repackage(
    component_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> ComponentDetailDto:
    parent = await components_service.get_component(component_id)

    validator = ComponentPermissionValidator(current_user)
    if not validator.can_update(parent):
        logger.warning(f"User {current_user.id} not permitted to repackage component {component_id}")
        raise ForbiddenException("Insufficient permission to repackage this component")

    logger.info(f"Repackaging component {component_id} from {parent.repo_url}")
    component = await components_service.repackage_component(parent)
    logger.info(f"Repackaging complete: '{component.name}' v{component.version} ({component.id})")
    # shares the parent's name/lineage, so it may already be favorited
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(component, component.name in favorited_names)


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
    component = await components_service.get_component(component_id)
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(component, component.name in favorited_names)


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
    component = await components_service.get_component(component_id)
    versions = await components_service.get_versions(component)
    favorited_names = await _favorited_names(favorites_service, current_user)
    return [ComponentTransformer.to_list_item(v, v.name in favorited_names) for v in versions]


@router.get(
    "/{component_id}/download",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def download(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> Response:
    component = await components_service.get_component(component_id)
    filename, content = await components_service.get_cwl_download(component)
    return Response(
        content=content,
        media_type="application/yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch(
    "/{component_id}",
    response_model=ComponentDetailDto,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_403_FORBIDDEN: {"model": ErrorResponse, "description": "Not the creator of this component"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": ErrorResponse, "description": "Request validation failed"},
    },
)
async def update(
    component_id: uuid.UUID,
    dto: UpdateComponentRequestDto,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> ComponentDetailDto:
    existing = await components_service.get_component(component_id)

    validator = ComponentPermissionValidator(current_user)
    if not validator.can_update(existing):
        logger.warning(f"User {current_user.id} not permitted to update component {component_id}")
        raise ForbiddenException("Insufficient permission to update this component")

    updated = ComponentTransformer.apply_update_dto(existing, dto)
    saved = await components_service.update_component(updated)
    logger.info(f"Updated component {saved.id}")
    favorited_names = await _favorited_names(favorites_service, current_user)
    return ComponentTransformer.to_detail(saved, saved.name in favorited_names)


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
        # last version of this lineage is gone - sweep any leftover favorites so they
        # don't become permanently orphaned (see FavoritesRepository.delete_by_component_name)
        await favorites_service.remove_all_favorites(component.name)


@router.post(
    "/{component_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
    },
)
async def add_favorite(
    component_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> None:
    await favorites_service.add_favorite(current_user.id, component_id)
    logger.info(f"User {current_user.id} favorited component {component_id}")


@router.delete(
    "/{component_id}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse, "description": "Missing or invalid credentials"},
        status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"},
    },
)
async def remove_favorite(
    component_id: uuid.UUID,
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    favorites_service: Annotated[FavoritesService, Depends(FavoritesService.get_service)],
) -> None:
    await favorites_service.remove_favorite(current_user.id, component_id)
    logger.info(f"User {current_user.id} unfavorited component {component_id}")


@router.get(
    "/{component_id}/bundle",
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse, "description": "Component not found"}},
)
async def bundle(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> Response:
    component = await components_service.get_component(component_id)
    filename, content = await components_service.get_bundle(component)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )