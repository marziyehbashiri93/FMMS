"""Guard for the one-open-fault/repair-flow-per-vehicle business rule.

Race-condition note:
    Service-level checks are the minimum enforcement layer. A PostgreSQL partial
    unique index on ``fault.vehicle_id`` where ``status <> 'CLOSED'`` would only
    cover faults, not active repair orders. Coordinating both aggregates atomically
    would require a dedicated workflow table or explicit row locking across two
    tables; that is intentionally out of scope for this milestone.
"""

from __future__ import annotations

import uuid

from apps.fault.domain.entities import FaultStatus
from apps.fault.domain.interfaces.fault_repository import IFaultRepository
from apps.repair.domain.entities import RepairOrderStatus
from apps.repair.domain.interfaces.repair_repository import IRepairOrderRepository
from core.exceptions.base_exception import FMMSStateError

FAULT_TERMINAL_STATUSES: frozenset[FaultStatus] = frozenset({FaultStatus.CLOSED})
FAULT_OPEN_STATUSES: frozenset[FaultStatus] = frozenset(
    status for status in FaultStatus if status not in FAULT_TERMINAL_STATUSES
)

REPAIR_ORDER_TERMINAL_STATUSES: frozenset[RepairOrderStatus] = frozenset(
    {
        RepairOrderStatus.COMPLETED,
        RepairOrderStatus.ACCEPTED_BY_DRIVER,
        RepairOrderStatus.REJECTED_BY_DRIVER,
        RepairOrderStatus.REJECTED_BY_TRANSPORT,
        RepairOrderStatus.NO_REPAIR_NEEDED,
        RepairOrderStatus.CANCELLED,
    }
)
REPAIR_ORDER_OPEN_STATUSES: frozenset[RepairOrderStatus] = frozenset(
    status
    for status in RepairOrderStatus
    if status not in REPAIR_ORDER_TERMINAL_STATUSES
)

VEHICLE_OPEN_FLOW_MESSAGE = (
    "برای این خودرو یک خرابی یا تعمیر باز وجود دارد. "
    "ابتدا وضعیت قبلی را تعیین تکلیف کنید."
)
VEHICLE_OPEN_FLOW_ERROR_CODE = "VEHICLE_HAS_OPEN_FAULT_OR_REPAIR"


def assert_vehicle_has_no_open_flow(
    vehicle_id: uuid.UUID,
    *,
    fault_repository: IFaultRepository,
    repair_order_repository: IRepairOrderRepository,
) -> None:
    """Raise when the vehicle already has an open fault or active repair order.

    Args:
        vehicle_id: Vehicle being checked.
        fault_repository: Fault persistence port.
        repair_order_repository: Repair-order persistence port.

    Raises:
        FMMSStateError: If an open fault or non-terminal repair order exists.
    """
    open_fault = fault_repository.has_open_fault_for_vehicle(vehicle_id)
    open_repair = repair_order_repository.has_open_repair_order_for_vehicle(vehicle_id)

    if not open_fault and not open_repair:
        return

    details: dict[str, object] = {"vehicle_id": str(vehicle_id)}
    if open_fault:
        details["has_open_fault"] = True
    if open_repair:
        active_repairs = repair_order_repository.list_active_by_vehicle(vehicle_id)
        details["active_repair_order_ids"] = [str(order.id) for order in active_repairs]

    raise FMMSStateError(
        message=VEHICLE_OPEN_FLOW_MESSAGE,
        error_code=VEHICLE_OPEN_FLOW_ERROR_CODE,
        details=details,
    )
