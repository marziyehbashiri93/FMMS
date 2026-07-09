"""PM application DTOs — pure Python, no ORM, no Django objects."""

from apps.preventive_maintenance.application.dto.pm_dto import (
    CompletePMWorkOrderDTO,
    CreatePMPlanDTO,
    PMPlanResponseDTO,
    PMWorkOrderResponseDTO,
    TriggerPMWorkOrderDTO,
)

__all__ = [
    "CreatePMPlanDTO",
    "TriggerPMWorkOrderDTO",
    "CompletePMWorkOrderDTO",
    "PMPlanResponseDTO",
    "PMWorkOrderResponseDTO",
]
