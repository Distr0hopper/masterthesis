import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Query, status
from fastapi.responses import Response

from app.api.dto.component import ComponentDetailDto, ComponentListItemDto, CreateComponentRequestDto
from app.api.transformer.component_transformer import to_detail, to_list_item
from app.application.service.auth_service import AuthService
from app.application.service.components_service import ComponentsService
from app.domain.models.component_domain import VALID_DOMAINS
from app.domain.models.user import User

router = APIRouter(prefix="/components", tags=["components"])

MAX_CWL_FILE_SIZE = 1024 * 1024


@router.get("", response_model=list[ComponentListItemDto])
async def list_components(
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
    # json_schema_extra adds the enum purely so Swagger UI renders a dropdown
    domain: Annotated[str | None, Query(json_schema_extra={"enum": VALID_DOMAINS})] = None,
) -> list[ComponentListItemDto]:
    components = await components_service.list_components(domain)
    return [to_list_item(c) for c in components]


@router.post("", response_model=ComponentDetailDto, status_code=status.HTTP_201_CREATED)
async def create(
    dto: Annotated[CreateComponentRequestDto, Form(media_type="multipart/form-data")],
    current_user: Annotated[User, Depends(AuthService.get_current_user)],
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ComponentDetailDto:
    content = await dto.cwl_file.read()
    if len(content) > MAX_CWL_FILE_SIZE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Validation failed (expected size to be less than {MAX_CWL_FILE_SIZE} bytes)",
        )

    component = await components_service.create_manual(
        name=dto.name,
        domain=dto.domain,
        cwl_content=content.decode("utf-8"),
        author_name=dto.author_name,
        repo_url=dto.repo_url,
        repo_commit_sha=dto.repo_commit_sha,
        description=dto.description,
        created_by_id=current_user.id,
    )
    return to_detail(component)


@router.get("/{component_id}", response_model=ComponentDetailDto)
async def get_component(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> ComponentDetailDto:
    component = await components_service.get_component(component_id)
    return to_detail(component)


@router.get("/{component_id}/versions", response_model=list[ComponentListItemDto])
async def get_versions(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> list[ComponentListItemDto]:
    versions = await components_service.get_versions(component_id)
    return [to_list_item(v) for v in versions]


@router.get("/{component_id}/download")
async def download(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> Response:
    filename, content = await components_service.get_cwl_download(component_id)
    return Response(
        content=content,
        media_type="application/yaml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{component_id}/bundle")
async def bundle(
    component_id: uuid.UUID,
    components_service: Annotated[ComponentsService, Depends(ComponentsService.get_service)],
) -> Response:
    filename, content = await components_service.get_bundle(component_id)
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )