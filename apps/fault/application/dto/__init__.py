"""Fault application DTOs — pure Python, no ORM, no Django objects."""

from apps.fault.application.dto.catalog_dto import (
    FaultCatalogResponseDTO,
    FaultCatalogSyncResultDTO,
)
from apps.fault.application.dto.fault_dto import (
    AssignFaultDTO,
    CloseFaultDTO,
    FaultResponseDTO,
    ReportFaultDTO,
)

__all__ = [
    "ReportFaultDTO",
    "AssignFaultDTO",
    "CloseFaultDTO",
    "FaultResponseDTO",
    "FaultCatalogResponseDTO",
    "FaultCatalogSyncResultDTO",
]
