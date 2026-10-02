from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.dto.common import ErrorResponse
from app.api.exception.exceptions import ForbiddenException
from app.application.exception.auth_exceptions import InvalidTokenError
from app.application.exception.component_exceptions import (
    AlreadyPackagedError,
    ComponentKindMismatchError,
    ComponentNameAlreadyExistsError,
    ComponentNotFoundError,
    InvalidCwlError,
    ManualUploadCannotBeRepackagedError,
    MissingCommandPayloadError,
    PackagedCommitChangedError,
    PackagingFailedError,
    PackagingServiceUnavailableError,
)
from app.application.exception.favorites_exceptions import FavoritesRequireAuthError
from app.application.exception.otp_exceptions import OtpRequestRateLimitedError
from app.application.exception.workflow_draft_exceptions import (
    ExportValidationError,
    WorkflowDraftForbiddenError,
    WorkflowDraftNotFoundError,
)
from app.application.exception.workflow_exceptions import (
    ConflictingAuxiliaryFileError,
    ConflictingStepFileError,
    DuplicateExtractedComponentNameError,
    ExtractedComponentNameCollisionError,
    InvalidComponentConfigError,
    InvalidExtractedComponentNameError,
    InvalidWorkflowArchiveError,
    InvalidWorkflowCwlError,
    MissingImportedFileError,
    NestedWorkflowsNotReadyError,
    PublishedWorkflowStepsLockedError,
    UnconfiguredWorkflowStepError,
    UnpublishableWorkflowComponentsError,
    WorkflowCycleError,
    WorkflowHasUnpublishedComponentsError,
    WorkflowNotReadyToPublishError,
    WorkflowStepNotFoundError,
    WorkflowStepNotMatchedError,
)
from app.domain.exception.login_code_exceptions import (
    InvalidOtpCodeError,
    OtpAttemptsExceededError,
    OtpCodeExpiredError,
)


async def _invalid_cwl_handler(request: Request, exc: InvalidCwlError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _packaging_failed_handler(request: Request, exc: PackagingFailedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _packaged_commit_changed_handler(request: Request, exc: PackagedCommitChangedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _packaging_service_unavailable_handler(request: Request, exc: PackagingServiceUnavailableError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=ErrorResponse(detail=str(exc)).model_dump())


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


async def _component_kind_mismatch_handler(request: Request, exc: ComponentKindMismatchError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _nested_workflows_not_ready_handler(request: Request, exc: NestedWorkflowsNotReadyError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _workflow_cycle_handler(request: Request, exc: WorkflowCycleError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _published_workflow_steps_locked_handler(
    request: Request, exc: PublishedWorkflowStepsLockedError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _workflow_step_not_found_handler(request: Request, exc: WorkflowStepNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_workflow_archive_handler(request: Request, exc: InvalidWorkflowArchiveError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_workflow_cwl_handler(request: Request, exc: InvalidWorkflowCwlError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _workflow_step_not_matched_handler(request: Request, exc: WorkflowStepNotMatchedError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _workflow_not_ready_to_publish_handler(request: Request, exc: WorkflowNotReadyToPublishError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _workflow_draft_not_found_handler(request: Request, exc: WorkflowDraftNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=ErrorResponse(detail=str(exc)).model_dump())


async def _workflow_draft_forbidden_handler(request: Request, exc: WorkflowDraftForbiddenError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=ErrorResponse(detail=str(exc)).model_dump())


async def _export_validation_handler(request: Request, exc: ExportValidationError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _missing_command_payload_handler(request: Request, exc: MissingCommandPayloadError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _conflicting_auxiliary_file_handler(
    request: Request, exc: ConflictingAuxiliaryFileError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _conflicting_step_file_handler(request: Request, exc: ConflictingStepFileError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _missing_imported_file_handler(request: Request, exc: MissingImportedFileError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _workflow_has_unpublished_components_handler(
    request: Request, exc: WorkflowHasUnpublishedComponentsError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _unpublishable_workflow_components_handler(
    request: Request, exc: UnpublishableWorkflowComponentsError
) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _unconfigured_workflow_step_handler(request: Request, exc: UnconfiguredWorkflowStepError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_component_config_handler(request: Request, exc: InvalidComponentConfigError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _invalid_extracted_component_name_handler(request: Request, exc: InvalidExtractedComponentNameError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _duplicate_extracted_component_name_handler(request: Request, exc: DuplicateExtractedComponentNameError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=ErrorResponse(detail=str(exc)).model_dump())


async def _extracted_component_name_collision_handler(request: Request, exc: ExtractedComponentNameCollisionError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=ErrorResponse(detail=str(exc)).model_dump())


async def _integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    # a concurrent change (e.g. a component deleted between lookup and save) - a conflict
    # the client can retry after reloading, not a server error. The DB message is not
    # echoed back: it would leak table/constraint names.
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=ErrorResponse(detail="The data changed while saving - please reload and try again").model_dump(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
    app.add_exception_handler(InvalidTokenError, _invalid_token_handler)
    app.add_exception_handler(InvalidOtpCodeError, _invalid_otp_code_handler)
    app.add_exception_handler(OtpCodeExpiredError, _otp_code_expired_handler)
    app.add_exception_handler(OtpAttemptsExceededError, _otp_attempts_exceeded_handler)
    app.add_exception_handler(OtpRequestRateLimitedError, _otp_rate_limited_handler)
    app.add_exception_handler(InvalidCwlError, _invalid_cwl_handler)
    app.add_exception_handler(PackagingFailedError, _packaging_failed_handler)
    app.add_exception_handler(PackagedCommitChangedError, _packaged_commit_changed_handler)
    app.add_exception_handler(PackagingServiceUnavailableError, _packaging_service_unavailable_handler)
    app.add_exception_handler(ManualUploadCannotBeRepackagedError, _manual_upload_cannot_be_repackaged_handler)
    app.add_exception_handler(AlreadyPackagedError, _already_packaged_handler)
    app.add_exception_handler(ComponentNameAlreadyExistsError, _component_name_already_exists_handler)
    app.add_exception_handler(ComponentNotFoundError, _component_not_found_handler)
    app.add_exception_handler(ForbiddenException, _forbidden_handler)
    app.add_exception_handler(FavoritesRequireAuthError, _favorites_require_auth_handler)
    app.add_exception_handler(ComponentKindMismatchError, _component_kind_mismatch_handler)
    app.add_exception_handler(NestedWorkflowsNotReadyError, _nested_workflows_not_ready_handler)
    app.add_exception_handler(WorkflowCycleError, _workflow_cycle_handler)
    app.add_exception_handler(PublishedWorkflowStepsLockedError, _published_workflow_steps_locked_handler)
    app.add_exception_handler(WorkflowStepNotFoundError, _workflow_step_not_found_handler)
    app.add_exception_handler(InvalidWorkflowArchiveError, _invalid_workflow_archive_handler)
    app.add_exception_handler(InvalidWorkflowCwlError, _invalid_workflow_cwl_handler)
    app.add_exception_handler(WorkflowStepNotMatchedError, _workflow_step_not_matched_handler)
    app.add_exception_handler(WorkflowNotReadyToPublishError, _workflow_not_ready_to_publish_handler)
    app.add_exception_handler(WorkflowDraftNotFoundError, _workflow_draft_not_found_handler)
    app.add_exception_handler(WorkflowDraftForbiddenError, _workflow_draft_forbidden_handler)
    app.add_exception_handler(ExportValidationError, _export_validation_handler)
    app.add_exception_handler(MissingCommandPayloadError, _missing_command_payload_handler)
    app.add_exception_handler(ConflictingAuxiliaryFileError, _conflicting_auxiliary_file_handler)
    app.add_exception_handler(ConflictingStepFileError, _conflicting_step_file_handler)
    app.add_exception_handler(MissingImportedFileError, _missing_imported_file_handler)
    app.add_exception_handler(
        WorkflowHasUnpublishedComponentsError, _workflow_has_unpublished_components_handler
    )
    app.add_exception_handler(UnpublishableWorkflowComponentsError, _unpublishable_workflow_components_handler)
    app.add_exception_handler(UnconfiguredWorkflowStepError, _unconfigured_workflow_step_handler)
    app.add_exception_handler(InvalidComponentConfigError, _invalid_component_config_handler)
    app.add_exception_handler(InvalidExtractedComponentNameError, _invalid_extracted_component_name_handler)
    app.add_exception_handler(DuplicateExtractedComponentNameError, _duplicate_extracted_component_name_handler)
    app.add_exception_handler(ExtractedComponentNameCollisionError, _extracted_component_name_collision_handler)
