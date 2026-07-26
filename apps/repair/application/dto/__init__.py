"""Repair application DTOs — pure Python, no ORM, no Django objects."""

from apps.repair.application.dto.repair_dto import (
    AddRepairActivityDTO,
    AddRepairPartDTO,
    AssignRepairOrderDTO,
    CloseRepairOrderDTO,
    CompleteRepairOrderDTO,
    CreateRepairOrderDTO,
    DeleteRepairActivityDTO,
    DeleteRepairPartDTO,
    RepairActivityResponseDTO,
    RepairOrderResponseDTO,
    RepairPartResponseDTO,
    SyncRepairToSAPDTO,
    UpdateRepairActivityDTO,
    UpdateRepairPartDTO,
)

__all__ = [
    "CreateRepairOrderDTO",
    "AssignRepairOrderDTO",
    "CloseRepairOrderDTO",
    "CompleteRepairOrderDTO",
    "AddRepairActivityDTO",
    "AddRepairPartDTO",
    "DeleteRepairActivityDTO",
    "DeleteRepairPartDTO",
    "UpdateRepairActivityDTO",
    "UpdateRepairPartDTO",
    "SyncRepairToSAPDTO",
    "RepairOrderResponseDTO",
    "RepairActivityResponseDTO",
    "RepairPartResponseDTO",
]
