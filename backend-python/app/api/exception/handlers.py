from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.dto.common import ErrorResponse
from app.api.exception.exceptions import ForbiddenException, NotFoundException
from app.application.exception.auth_exceptions import InvalidCredentialsError, InvalidTokenError
from app.application.exception.component_exceptions import InvalidCwlError
from app.domain.exception.user_exceptions import EmailAlreadyRegisteredError

async def _email_already_registered_handler(request: Request, exc: EmailAlreadyRegisteredError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_cwl_handler(request: Request, exc: InvalidCwlError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_credentials_handler(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


async def _not_found_handler(request: Request, exc: NotFoundException) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=ErrorResponse(detail=str(exc)).model_dump())


async def _forbidden_handler(request: Request, exc: ForbiddenException) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=ErrorResponse(detail=str(exc)).model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(EmailAlreadyRegisteredError, _email_already_registered_handler)
    app.add_exception_handler(InvalidCredentialsError, _invalid_credentials_handler)
    app.add_exception_handler(InvalidTokenError, _invalid_token_handler)
    app.add_exception_handler(InvalidCwlError, _invalid_cwl_handler)
    app.add_exception_handler(NotFoundException, _not_found_handler)
    app.add_exception_handler(ForbiddenException, _forbidden_handler)