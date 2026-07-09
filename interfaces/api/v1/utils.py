"""Small HTTP-to-application boundary helpers."""

from __future__ import annotations

import uuid
from typing import Any

from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet


def request_id_from(request: Request) -> str:
    """Return the request correlation identifier."""
    return str(
        getattr(request, "request_id", "") or request.headers.get("X-Request-ID", "")
    )


def user_id_from(request: Request) -> uuid.UUID:
    """Return the authenticated user's UUID."""
    return uuid.UUID(str(request.user.id))


def paginate_dto_list(view: GenericViewSet, items: list[Any]) -> list[Any] | None:
    """Paginate a list of DTOs/entities for service-backed list endpoints.

    DRF stubs type ``paginate_queryset`` for QuerySets; FMMS list services return
    plain lists, which are supported at runtime.
    """
    return view.paginate_queryset(items)  # type: ignore[arg-type]
