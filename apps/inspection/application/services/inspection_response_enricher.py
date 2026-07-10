"""Enrich inspection response DTOs with history fields for manager demo views."""

from __future__ import annotations

import uuid

from apps.driver.domain.interfaces.driver_repository import IDriverRepository
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.inspection.application.dto.inspection_dto import (
    InspectionDriverSummaryDTO,
    InspectionResponseDTO,
)
from apps.inspection.domain.entities import Inspection


def enrich_inspection_response(
    inspection: Inspection,
    dto: InspectionResponseDTO,
    fault_repository: IFaultRepository | None = None,
    driver_repository: IDriverRepository | None = None,
) -> InspectionResponseDTO:
    """Attach derived history fields to an inspection response DTO."""
    related_fault_ids: list[uuid.UUID] = []
    if fault_repository is not None:
        related_fault_ids = [
            f.id for f in fault_repository.list_by_inspection(inspection.id)
        ]

    driver_summary = None
    if inspection.driver_id and driver_repository is not None:
        try:
            driver = driver_repository.get_by_id(inspection.driver_id)
            driver_summary = InspectionDriverSummaryDTO(
                id=driver.id,
                name=driver.full_name,
            )
        except Exception:
            driver_summary = None

    overall_result = "FAIL" if inspection.has_failures else "PASS"

    return InspectionResponseDTO(
        id=dto.id,
        vehicle_id=dto.vehicle_id,
        inspection_type=dto.inspection_type,
        odometer_value=dto.odometer_value,
        odometer_unit=dto.odometer_unit,
        status=dto.status,
        inspected_at=dto.inspected_at,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
        items=dto.items,
        driver_id=dto.driver_id,
        reviewed_by_id=dto.reviewed_by_id,
        review_notes=dto.review_notes,
        has_failures=dto.has_failures,
        overall_result=overall_result,
        related_fault_ids=related_fault_ids,
        driver=driver_summary,
    )
