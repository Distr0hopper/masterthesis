from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.application.exception.auth_exceptions import InvalidCredentialsError, InvalidTokenError
from app.domain.exception.component_exceptions import ComponentNotFoundError
from app.domain.exception.user_exceptions import EmailAlreadyRegisteredError


async def _email_already_registered_handler(request: Request, exc: EmailAlreadyRegisteredError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": str(exc)})


async def _component_not_found_handler(request: Request, exc: ComponentNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": str(exc)})


async def _invalid_credentials_handler(request: Request, exc: InvalidCredentialsError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)})


async def _invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"detail": str(exc)})


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(EmailAlreadyRegisteredError, _email_already_registered_handler)
    app.add_exception_handler(InvalidCredentialsError, _invalid_credentials_handler)
    app.add_exception_handler(InvalidTokenError, _invalid_token_handler)
    app.add_exception_handler(ComponentNotFoundError, _component_not_found_handler)
