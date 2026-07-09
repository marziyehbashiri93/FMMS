"""
FMMS Audit Log Middleware.

Logs all mutating HTTP requests (POST, PUT, PATCH, DELETE) with structured
fields including user identity, path, method, status code, and duration.
This provides an immutable audit trail of all state-changing operations.
"""

import time

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger(domain="security", module=__name__)

MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AuditLogMiddleware(MiddlewareMixin):
    """
    Middleware that produces a structured audit log entry for every
    mutating HTTP request (POST, PUT, PATCH, DELETE).

    Log entries include: request_id, user_id, method, path,
    status_code, duration_ms.
    """

    def process_request(self, request: HttpRequest) -> None:
        """
        Record the request start time for duration calculation.

        Args:
            request: The incoming HTTP request.
        """
        if request.method in MUTATING_METHODS:
            request._audit_start_time = time.monotonic()  # type: ignore[attr-defined]

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse,
    ) -> HttpResponse:
        """
        Emit an audit log entry for completed mutating requests.

        Args:
            request: The completed HTTP request.
            response: The HTTP response being returned.

        Returns:
            The unchanged response.
        """
        if request.method not in MUTATING_METHODS:
            return response

        start_time: float | None = getattr(request, "_audit_start_time", None)
        duration_ms: float | None = (
            round((time.monotonic() - start_time) * 1000, 2)
            if start_time is not None
            else None
        )

        user = getattr(request, "user", None)
        user_id: str | None = str(user.pk) if user and user.is_authenticated else None
        request_id: str | None = getattr(request, "request_id", None)

        logger.info(
            "Audit: %s %s → %s",
            request.method,
            request.path,
            response.status_code,
            extra={
                "request_id": request_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "content_type": request.content_type,
            },
        )

        return response
