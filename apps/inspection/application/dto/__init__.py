"""Inspection application DTOs — pure Python, no ORM, no Django objects."""

from apps.inspection.application.dto.inspection_dto import (
    AddInspectionItemDTO,
    CreateInspectionDTO,
    InspectionItemResponseDTO,
    InspectionResponseDTO,
    ReportInspectionFaultDTO,
    SubmitInspectionDTO,
)

__all__ = [
    "CreateInspectionDTO",
    "AddInspectionItemDTO",
    "SubmitInspectionDTO",
    "ReportInspectionFaultDTO",
    "InspectionResponseDTO",
    "InspectionItemResponseDTO",
]
