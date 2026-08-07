from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.dto.common import ErrorResponse
from app.api.exception.exceptions import ForbiddenException
from app.application.exception.auth_exceptions import InvalidTokenError
from app.application.exception.component_exceptions import (
    AlreadyPackagedError,
    ComponentNameAlreadyExistsError,
    ComponentNotFoundError,
    InvalidCwlError,
    ManualUploadCannotBeRepackagedError,
    PackagingFailedError,
)
from app.application.exception.favorites_exceptions import FavoritesRequireAuthError
from app.application.exception.otp_exceptions import OtpRequestRateLimitedError
from app.domain.exception.login_code_exceptions import (
    InvalidOtpCodeError,
    OtpAttemptsExceededError,
    OtpCodeExpiredError,
)


async def _invalid_cwl_handler(request: Request, exc: InvalidCwlError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _packaging_failed_handler(request: Request, exc: PackagingFailedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _manual_upload_cannot_be_repackaged_handler(request: Request, exc: ManualUploadCannotBeRepackagedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _already_packaged_handler(request: Request, exc: AlreadyPackagedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _component_name_already_exists_handler(request: Request, exc: ComponentNameAlreadyExistsError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_token_handler(request: Request, exc: InvalidTokenError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_otp_code_handler(request: Request, exc: InvalidOtpCodeError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


async def _otp_code_expired_handler(request: Request, exc: OtpCodeExpiredError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


async def _otp_attempts_exceeded_handler(request: Request, exc: OtpAttemptsExceededError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


async def _otp_rate_limited_handler(request: Request, exc: OtpRequestRateLimitedError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=ErrorResponse(detail=str(exc)).model_dump(),
        headers={"Retry-After": str(exc.retry_after_seconds)},
    )


async def _component_not_found_handler(request: Request, exc: ComponentNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=ErrorResponse(detail=str(exc)).model_dump())


async def _forbidden_handler(request: Request, exc: ForbiddenException) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=ErrorResponse(detail=str(exc)).model_dump())


async def _favorites_require_auth_handler(request: Request, exc: FavoritesRequireAuthError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content=ErrorResponse(detail=str(exc)).model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(InvalidTokenError, _invalid_token_handler)
    app.add_exception_handler(InvalidOtpCodeError, _invalid_otp_code_handler)
    app.add_exception_handler(OtpCodeExpiredError, _otp_code_expired_handler)
    app.add_exception_handler(OtpAttemptsExceededError, _otp_attempts_exceeded_handler)
    app.add_exception_handler(OtpRequestRateLimitedError, _otp_rate_limited_handler)
    app.add_exception_handler(InvalidCwlError, _invalid_cwl_handler)
    app.add_exception_handler(PackagingFailedError, _packaging_failed_handler)
    app.add_exception_handler(ManualUploadCannotBeRepackagedError, _manual_upload_cannot_be_repackaged_handler)
    app.add_exception_handler(AlreadyPackagedError, _already_packaged_handler)
    app.add_exception_handler(ComponentNameAlreadyExistsError, _component_name_already_exists_handler)
    app.add_exception_handler(ComponentNotFoundError, _component_not_found_handler)
    app.add_exception_handler(ForbiddenException, _forbidden_handler)
    app.add_exception_handler(FavoritesRequireAuthError, _favorites_require_auth_handler)