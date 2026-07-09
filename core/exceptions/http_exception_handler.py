"""
FMMS DRF Exception Handler.

Maps FMMS domain exceptions and DRF exceptions to the standard
FMMS error response format:

    {
        "error_code": "NOT_FOUND",
        "message": "The requested resource was not found.",
        "details": {},
        "request_id": "uuid-..."
    }

Registered in settings.REST_FRAMEWORK['EXCEPTION_HANDLER'].
"""

import logging
from typing import Any

from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    PermissionDenied,
    ValidationError,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from core.exceptions.base_exception import (
    FMMSBaseException,
    FMMSConflictError,
    FMMSIntegrationError,
    FMMSNotFoundError,
    FMMSPermissionError,
    FMMSStateError,
    FMMSValidationError,
)

logger = logging.getLogger("fmms.core.exceptions")


def _build_error_response(
    error_code: str,
    message: str,
    details: dict[str, Any],
    request_id: str | None,
    http_status: int,
) -> Response:
    """
    Build a standardized FMMS error response.

    Args:
        error_code: Machine-readable error code.
        message: Human-readable error message.
        details: Additional context dictionary.
        request_id: Correlation ID from X-Request-ID header.
        http_status: HTTP status code to return.

    Returns:
        A DRF Response with the standard FMMS error body.
    """
    return Response(
        {
            "error_code": error_code,
            "message": message,
            "details": details,
            "request_id": request_id,
        },
        status=http_status,
    )


def fmms_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    """
    Custom DRF exception handler for FMMS.

    Maps both FMMS domain exceptions and standard DRF/Django exceptions
    to the unified error response format. Unhandled exceptions return None,
    which causes DRF to fall back to its default 500 handling.

    Args:
        exc: The exception that was raised.
        context: DRF context dict containing 'request' and 'view'.

    Returns:
        A Response with a standardized error body, or None if unhandled.
    """
    request: Request | None = context.get("request")
    request_id: str | None = getattr(request, "request_id", None) if request else None

    # ── FMMS Domain Exceptions ────────────────────────────────────────────────
    if isinstance(exc, FMMSNotFoundError):
        logger.warning(
            "Resource not found: %s",
            exc.message,
            extra={"domain": "core", "request_id": request_id},
        )
        return _build_error_response(
            exc.error_code,
            exc.message,
            exc.details,
            request_id,
            status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, FMMSValidationError):
        logger.warning(
            "Validation error: %s",
            exc.message,
            extra={"domain": "core", "request_id": request_id},
        )
        return _build_error_response(
            exc.error_code,
            exc.message,
            exc.details,
            request_id,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if isinstance(exc, FMMSPermissionError):
        logger.warning(
            "Permission denied: %s",
            exc.message,
            extra={"domain": "core", "request_id": request_id},
        )
        return _build_error_response(
            exc.error_code,
            exc.message,
            exc.details,
            request_id,
            status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, FMMSConflictError):
        logger.warning(
            "Conflict: %s",
            exc.message,
            extra={"domain": "core", "request_id": request_id},
        )
        return _build_error_response(
            exc.error_code,
            exc.message,
            exc.details,
            request_id,
            status.HTTP_409_CONFLICT,
        )

    if isinstance(exc, FMMSStateError):
        logger.warning(
            "Invalid state transition: %s",
            exc.message,
            extra={"domain": "core", "request_id": request_id},
        )
        return _build_error_response(
            exc.error_code,
            exc.message,
            exc.details,
            request_id,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    if isinstance(exc, FMMSIntegrationError):
        logger.error(
            "Integration error: %s",
            exc.message,
            extra={"domain": "integration", "request_id": request_id},
        )
        return _build_error_response(
            exc.error_code,
            exc.message,
            exc.details,
            request_id,
            status.HTTP_502_BAD_GATEWAY,
        )

    if isinstance(exc, FMMSBaseException):
        logger.error(
            "Unclassified FMMS error: %s",
            exc.message,
            extra={"domain": "core", "request_id": request_id},
        )
        return _build_error_response(
            exc.error_code,
            exc.message,
            exc.details,
            request_id,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # ── Django / DRF Exceptions ───────────────────────────────────────────────
    if isinstance(exc, Http404):
        return _build_error_response(
            "NOT_FOUND",
            "The requested resource was not found.",
            {},
            request_id,
            status.HTTP_404_NOT_FOUND,
        )

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return _build_error_response(
            "AUTHENTICATION_REQUIRED",
            "Authentication credentials were not provided or are invalid.",
            {},
            request_id,
            status.HTTP_401_UNAUTHORIZED,
        )

    if isinstance(exc, PermissionDenied):
        return _build_error_response(
            "PERMISSION_DENIED",
            "You do not have permission to perform this action.",
            {},
            request_id,
            status.HTTP_403_FORBIDDEN,
        )

    if isinstance(exc, ValidationError):
        return _build_error_response(
            "VALIDATION_ERROR",
            "Request validation failed.",
            (
                exc.detail
                if isinstance(exc.detail, dict)
                else {"non_field_errors": exc.detail}
            ),
            request_id,
            status.HTTP_400_BAD_REQUEST,
        )

    # Delegate remaining DRF exceptions to default handler
    response = exception_handler(exc, context)
    if response is not None:
        original_data = response.data
        response.data = {
            "error_code": "ERROR",
            "message": str(exc),
            "details": (
                original_data
                if isinstance(original_data, dict)
                else {"detail": original_data}
            ),
            "request_id": request_id,
        }
        return response

    # Unhandled — let Django's 500 handler take over
    logger.exception(
        "Unhandled exception in view",
        exc_info=exc,
        extra={"domain": "core", "request_id": request_id},
    )
    return None
