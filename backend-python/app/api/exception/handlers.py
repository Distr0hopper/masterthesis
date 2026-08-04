from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.dto.common import ErrorResponse
from app.api.exception.exceptions import ForbiddenException
from app.application.exception.auth_exceptions import InvalidCredentialsError, InvalidTokenError
from app.application.exception.component_exceptions import (
    AlreadyPackagedError,
    ComponentNotFoundError,
    InvalidCwlError,
    ManualUploadCannotBeRepackagedError,
    PackagingFailedError,
)
from app.domain.exception.user_exceptions import EmailAlreadyRegisteredError


async def _email_already_registered_handler(request: Request, exc: EmailAlreadyRegisteredError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_cwl_handler(request: Request, exc: InvalidCwlError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _packaging_failed_handler(request: Request, exc: PackagingFailedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _manual_upload_cannot_be_repackaged_handler(request: Request, exc: ManualUploadCannotBeRepackagedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _already_packaged_handler(request: Request, exc: AlreadyPackagedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_credentials_handler(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


async def _component_not_found_handler(request: Request, exc: ComponentNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=ErrorResponse(detail=str(exc)).model_dump())


async def _forbidden_handler(request: Request, exc: ForbiddenException) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=ErrorResponse(detail=str(exc)).model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(EmailAlreadyRegisteredError, _email_already_registered_handler)
    app.add_exception_handler(InvalidCredentialsError, _invalid_credentials_handler)
    app.add_exception_handler(InvalidTokenError, _invalid_token_handler)
    app.add_exception_handler(InvalidCwlError, _invalid_cwl_handler)
    app.add_exception_handler(PackagingFailedError, _packaging_failed_handler)
    app.add_exception_handler(ManualUploadCannotBeRepackagedError, _manual_upload_cannot_be_repackaged_handler)
    app.add_exception_handler(AlreadyPackagedError, _already_packaged_handler)
    app.add_exception_handler(ComponentNotFoundError, _component_not_found_handler)
    app.add_exception_handler(ForbiddenException, _forbidden_handler)