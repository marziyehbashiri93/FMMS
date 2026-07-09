"""SAP PM Work Order DTOs.

A PM Order (Maintenance Order) represents planned or corrective work
to be executed on equipment. FMMS creates PM Orders in SAP for repair
and preventive maintenance activities.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CreatePMOrderRequest:
    """Request data required to create a PM Order in SAP.

    Attributes:
        equipment_number: SAP equipment number of the target vehicle.
        order_type: SAP order type code (e.g. corrective or preventive).
        description: Short description of the work to be carried out.
        planned_start: UTC datetime when work is planned to begin.
        notification_number: Optional PM notification that triggered this order.
        planned_end: Optional UTC datetime when work is planned to finish.
        work_center: Optional SAP work centre responsible for execution.
        plant: Optional SAP plant where the work is performed.
    """

    equipment_number: str
    order_type: str
    description: str
    planned_start: datetime
    notification_number: str | None = None
    planned_end: datetime | None = None
    work_center: str | None = None
    plant: str | None = None


@dataclass(frozen=True)
class SAPPMOrderDTO:
    """Result returned by SAP after creating or retrieving a PM Order.

    Attributes:
        order_number: The SAP-assigned order number.
        equipment_number: The equipment number the order is against.
        order_type: The SAP order type code.
        status: Current SAP system status of the order.
        planned_start: Optional planned start datetime.
        planned_end: Optional planned end datetime.
        notification_number: Optional linked PM notification number.
    """

    order_number: str
    equipment_number: str
    order_type: str
    status: str
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    notification_number: str | None = None
