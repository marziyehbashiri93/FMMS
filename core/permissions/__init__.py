"""Authorization primitives for FMMS interfaces."""

from core.permissions.role_permissions import (
    IsAdminRole,
    IsFMMSAuthenticated,
    IsReadOnlyOrTechnicianOrAbove,
    IsSupervisorOrAbove,
    IsTechnicianOrAbove,
)

__all__ = [
    "IsAdminRole",
    "IsFMMSAuthenticated",
    "IsReadOnlyOrTechnicianOrAbove",
    "IsSupervisorOrAbove",
    "IsTechnicianOrAbove",
]
