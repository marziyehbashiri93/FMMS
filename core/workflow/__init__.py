"""Cross-domain workflow helpers shared by application services."""

from core.workflow.vehicle_open_flow import (
    FAULT_OPEN_STATUSES,
    FAULT_TERMINAL_STATUSES,
    REPAIR_ORDER_OPEN_STATUSES,
    REPAIR_ORDER_TERMINAL_STATUSES,
    VEHICLE_OPEN_FLOW_ERROR_CODE,
    VEHICLE_OPEN_FLOW_MESSAGE,
    assert_vehicle_has_no_open_flow,
)

__all__ = [
    "FAULT_OPEN_STATUSES",
    "FAULT_TERMINAL_STATUSES",
    "REPAIR_ORDER_OPEN_STATUSES",
    "REPAIR_ORDER_TERMINAL_STATUSES",
    "VEHICLE_OPEN_FLOW_ERROR_CODE",
    "VEHICLE_OPEN_FLOW_MESSAGE",
    "assert_vehicle_has_no_open_flow",
]
