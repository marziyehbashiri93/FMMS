"""Repair application DTOs — pure Python, no ORM, no Django objects."""

from apps.repair.application.dto.repair_dto import (
    AddRepairActivityDTO,
    AddRepairPartDTO,
    AssignRepairOrderDTO,
    CloseRepairOrderDTO,
    CompleteRepairOrderDTO,
    CreateRepairOrderDTO,
    RepairActivityResponseDTO,
    RepairOrderResponseDTO,
    RepairPartResponseDTO,
    SyncRepairToSAPDTO,
)

__all__ = [
    "CreateRepairOrderDTO",
    "AssignRepairOrderDTO",
    "CloseRepairOrderDTO",
    "CompleteRepairOrderDTO",
    "AddRepairActivityDTO",
    "AddRepairPartDTO",
    "SyncRepairToSAPDTO",
    "RepairOrderResponseDTO",
    "RepairActivityResponseDTO",
    "RepairPartResponseDTO",
]
