"""Authorization primitives for FMMS interfaces."""

from core.permissions.role_permissions import (
    IsAdminRole,
    IsDistributionSupervisorOrAbove,
    IsDriverOrTechnicianOrAbove,
    IsFMMSAuthenticated,
    IsReadOnlyOrDriverOrTechnicianOrAbove,
    IsReadOnlyOrTechnicianOrAbove,
    IsSupervisorOrAbove,
    IsTechnicianOrAbove,
    IsTransportSupervisorOrAbove,
    IsWorkshopSupervisorOrAbove,
)

__all__ = [
    "IsAdminRole",
    "IsDistributionSupervisorOrAbove",
    "IsDriverOrTechnicianOrAbove",
    "IsFMMSAuthenticated",
    "IsReadOnlyOrDriverOrTechnicianOrAbove",
    "IsReadOnlyOrTechnicianOrAbove",
    "IsSupervisorOrAbove",
    "IsTechnicianOrAbove",
    "IsTransportSupervisorOrAbove",
    "IsWorkshopSupervisorOrAbove",
]
