"""SAP PM Notification DTOs.

A PM Notification records a fault or malfunction against equipment in SAP.
It is created in SAP when FMMS identifies a fault and initiates corrective action.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CreatePMNotificationRequest:
    """Request data required to create a PM Notification in SAP.

    Attributes:
        equipment_number: SAP equipment number of the affected vehicle.
        fault_description: Free-text description of the reported fault.
        defect_code: SAP defect code identifying the type of fault.
        priority: SAP priority code ("1"=Very High, "2"=High, "3"=Medium, "4"=Low).
        reported_by: Identifier of the person reporting the fault (SAP user or name).
        reported_at: UTC datetime when the fault was reported.
        notification_type: SAP notification type. Fault reports use ``EM``.
        functional_location: Optional SAP functional location for the equipment.
        code_group: Optional defect code group within the catalog.
    """

    equipment_number: str
    fault_description: str
    defect_code: str
    priority: str
    reported_by: str
    reported_at: datetime
    notification_type: str = "EM"
    functional_location: str | None = None
    code_group: str | None = None


@dataclass(frozen=True)
class SAPNotificationDTO:
    """Result returned by SAP after creating a PM Notification.

    Attributes:
        notification_number: The SAP-assigned notification number.
        equipment_number: The equipment number the notification is against.
        status: The current SAP notification status code.
        created_at: UTC datetime when the notification was created in SAP.
    """

    notification_number: str
    equipment_number: str
    status: str
    created_at: datetime
