"""Service that orchestrates reporting of a new fault.

Cross-domain check performed here:
- Vehicle must exist (verified via IVehicleRepository).

Value-object validation (FaultCode format, FaultDescription length) is
delegated to the domain layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from apps.authentication.domain.interfaces.user_profile_reader import IUserProfileReader
from apps.fault.application.dto.fault_dto import (
    FaultItemResponseDTO,
    FaultResponseDTO,
    ReportFaultDTO,
)
from apps.fault.domain.entities import Fault, FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.fault.domain.value_objects import FaultCode, FaultDescription
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from apps.vehicle.domain.interfaces.vehicle_repository import IVehicleRepository
from core.exceptions.translation import load_or_not_found
from core.logging.structured_logger import get_structured_logger
from core.workflow import assert_vehicle_has_no_open_flow

logger = get_structured_logger("fault", __name__)


def _to_response_dto(
    fault: Fault,
    profile_reader: IUserProfileReader | None = None,
) -> FaultResponseDTO:
    """Map a ``Fault`` domain entity to a ``FaultResponseDTO``."""
    created_by = None
    if profile_reader is not None:
        created_by = profile_reader.get_profile(fault.reported_by_id)
    return FaultResponseDTO(
        id=fault.id,
        vehicle_id=fault.vehicle_id,
        code=fault.code.value,
        description=fault.description.value,
        severity=fault.severity,
        status=fault.status,
        reported_by_id=fault.reported_by_id,
        reported_at=fault.reported_at,
        created_at=fault.created_at,
        updated_at=fault.updated_at,
        inspection_id=fault.inspection_id,
        assigned_to_id=fault.assigned_to_id,
        sap_notification_number=fault.sap_notification_number,
        items=[
            FaultItemResponseDTO(
                id=item.id,
                component=item.component,
                description=item.description,
                severity=item.severity,
                inspection_item_id=item.inspection_item_id,
            )
            for item in fault.items
        ],
        created_by=created_by,
    )


class ReportFaultService:
    """Orchestrates reporting of a new fault.

    Args:
        fault_repository: Concrete ``IFaultRepository``.
        vehicle_repository: Concrete ``IVehicleRepository`` for cross-domain
            vehicle existence check.
        repair_order_repository: Used to enforce one open fault/repair flow
            per vehicle.
        profile_reader: Optional resolver for ``created_by`` enrichment.
    """

    def __init__(
        self,
        fault_repository: IFaultRepository,
        vehicle_repository: IVehicleRepository,
        repair_order_repository: IRepairOrderRepository,
        profile_reader: IUserProfileReader | None = None,
    ) -> None:
        self._fault_repo = fault_repository
        self._vehicle_repo = vehicle_repository
        self._repair_repo = repair_order_repository
        self._profile_reader = profile_reader

    def execute(self, dto: ReportFaultDTO) -> FaultResponseDTO:
        """Report and persist a new fault.

        Args:
            dto: Input data for the fault to report.

        Returns:
            ``FaultResponseDTO`` in OPEN status.

        Raises:
            FMMSNotFoundError: If no vehicle with ``dto.vehicle_id`` exists.
            FMMSStateError: If the vehicle already has an open fault or repair flow.
            ValueError: If ``FaultCode`` or ``FaultDescription`` validation fails.
        """
        logger.info(
            "Reporting fault",
            extra={
                "domain": "fault",
                "service": "ReportFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "vehicle_id": str(dto.vehicle_id),
                "severity": dto.severity,
            },
        )

        load_or_not_found(
            lambda: self._vehicle_repo.get_by_id(dto.vehicle_id),
            message=f"Vehicle '{dto.vehicle_id}' not found.",
            details={"vehicle_id": str(dto.vehicle_id)},
        )

        assert_vehicle_has_no_open_flow(
            dto.vehicle_id,
            fault_repository=self._fault_repo,
            repair_order_repository=self._repair_repo,
        )

        now = datetime.now(tz=UTC)
        fault = Fault(
            id=uuid.uuid4(),
            vehicle_id=dto.vehicle_id,
            code=FaultCode(dto.code),
            description=FaultDescription(dto.description),
            severity=dto.severity,
            status=FaultStatus.OPEN,
            reported_by_id=dto.reported_by,
            reported_at=now,
            inspection_id=dto.inspection_id,
            created_at=now,
            updated_at=now,
        )

        saved = self._fault_repo.save(fault)

        logger.info(
            "Fault reported successfully",
            extra={
                "domain": "fault",
                "service": "ReportFaultService",
                "operation": "execute",
                "request_id": dto.request_id,
                "entity_id": str(saved.id),
                "result": "success",
            },
        )

        return _to_response_dto(saved, self._profile_reader)
