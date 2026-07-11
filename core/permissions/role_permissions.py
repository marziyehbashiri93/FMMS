"""Role-based permission classes for the FMMS REST API.

Permissions inspect ``request.user.role`` on the custom ``FMMSUser`` model.
They contain no business rules — only authorization gates for the API layer.
"""

from __future__ import annotations

from typing import Any

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


def _normalized_role(user: Any) -> str | None:
    """Map legacy/demo roles to canonical FMMS authorization roles."""
    role = getattr(user, "role", None)
    role_map = {
        "DISTRIBUTION": "SUPERVISOR",
        "TRANSPORT": "SUPERVISOR",
        "WAREHOUSE": "SUPERVISOR",
        "DRIVER": "TECHNICIAN",
    }
    if role in role_map:
        return role_map[role]
    return role


class IsFMMSAuthenticated(BasePermission):
    """Require an authenticated FMMS user."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return True when the request has an authenticated user."""
        return bool(request.user and request.user.is_authenticated)


class IsAdminRole(BasePermission):
    """Allow only users with the ADMIN role."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return True for authenticated ADMIN users."""
        user: Any = request.user
        return bool(
            user and user.is_authenticated and _normalized_role(user) == "ADMIN"
        )


class IsSupervisorOrAbove(BasePermission):
    """Allow ADMIN or SUPERVISOR roles."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return True for ADMIN or SUPERVISOR users."""
        user: Any = request.user
        return bool(
            user
            and user.is_authenticated
            and _normalized_role(user) in {"ADMIN", "SUPERVISOR"}
        )


class IsTechnicianOrAbove(BasePermission):
    """Allow ADMIN, SUPERVISOR, or TECHNICIAN roles."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return True for operational roles including technicians."""
        user: Any = request.user
        return bool(
            user
            and user.is_authenticated
            and _normalized_role(user) in {"ADMIN", "SUPERVISOR", "TECHNICIAN"}
        )


class IsReadOnlyOrTechnicianOrAbove(BasePermission):
    """Allow any authenticated user for SAFE methods; writers need TECHNICIAN+.

    VIEWER may read. Mutating methods require TECHNICIAN, SUPERVISOR, or ADMIN.
    """

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Gate write access by role while allowing authenticated reads."""
        user: Any = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _normalized_role(user) in {"ADMIN", "SUPERVISOR", "TECHNICIAN"}


class IsTransportSupervisorOrAbove(BasePermission):
    """Allow transport/supervisor/admin roles for workflow approvals."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        """Return True for users mapped to supervisor privileges."""
        user: Any = request.user
        return bool(
            user
            and user.is_authenticated
            and _normalized_role(user) in {"ADMIN", "SUPERVISOR"}
        )
