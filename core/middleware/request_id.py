"""
FMMS Request ID Middleware.

Generates or propagates a unique X-Request-ID for every HTTP request.
The ID is attached to request.request_id and returned in the response header.
All downstream log records can reference this ID for correlation.
"""

import uuid

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin


class RequestIDMiddleware(MiddlewareMixin):
    """
    Middleware that assigns a unique request ID to every incoming HTTP request.

    If the client sends an 'X-Request-ID' header, that value is reused.
    Otherwise a new UUID4 is generated. The ID is:
    - Attached to request.request_id
    - Returned in the 'X-Request-ID' response header
    - Available to all log records via structured logging context
    """

    REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"
    RESPONSE_HEADER = "X-Request-ID"

    def process_request(self, request: HttpRequest) -> None:
        """
        Inject a request ID into the request object.

        Args:
            request: The incoming HTTP request.
        """
        incoming_id = request.META.get(self.REQUEST_ID_HEADER, "").strip()
        request.request_id = incoming_id if incoming_id else str(uuid.uuid4())  # type: ignore[attr-defined]

    def process_response(
        self,
        request: HttpRequest,
        response: HttpResponse,
    ) -> HttpResponse:
        """
        Attach the request ID to the HTTP response header.

        Args:
            request: The HTTP request (with request_id attached).
            response: The HTTP response being returned.

        Returns:
            The response with X-Request-ID header set.
        """
        request_id: str | None = getattr(request, "request_id", None)
        if request_id:
            response[self.RESPONSE_HEADER] = request_id
        return response
