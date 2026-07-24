"""Django read model for current driver vehicle assignments."""

from __future__ import annotations

from django.db.models import Q

from apps.driver.application.dto.driver_dto import DriverAssignedVehicleDTO
from apps.driver.application.interfaces.vehicle_assignment_reader import (
    IDriverVehicleAssignmentReader,
)
from apps.vehicle.infrastructure.models import VehicleModel
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("driver", __name__)


class DjangoDriverVehicleAssignmentReader(IDriverVehicleAssignmentReader):
    """Resolve current vehicle assignments from vehicle read data."""

    def vehicles_by_driver_customer_numbers(
        self,
        customer_numbers: set[str],
    ) -> tuple[
        dict[str, DriverAssignedVehicleDTO],
        dict[str, DriverAssignedVehicleDTO],
    ]:
        """Batch-load current vehicles keyed by driver customer number."""
        if not customer_numbers:
            return {}, {}

        vehicles = (
            VehicleModel.objects.filter(is_deleted=False)
            .filter(
                Q(driver1_customer_number__in=customer_numbers)
                | Q(driver2_customer_number__in=customer_numbers)
            )
            .order_by("-updated_at")
        )

        as_driver: dict[str, DriverAssignedVehicleDTO] = {}
        as_assistant: dict[str, DriverAssignedVehicleDTO] = {}
        for vehicle in vehicles:
            dto = DriverAssignedVehicleDTO(
                id=vehicle.id,
                vehicle_number=vehicle.vehicle_number,
                license_plate=vehicle.license_plate,
            )
            driver1 = vehicle.driver1_customer_number
            driver2 = vehicle.driver2_customer_number
            if driver1 and driver1 in customer_numbers:
                if driver1 in as_driver:
                    _log_duplicate_assignment(driver1, "DRIVER", vehicle.id)
                else:
                    as_driver[driver1] = dto
            if driver2 and driver2 in customer_numbers:
                if driver2 in as_assistant:
                    _log_duplicate_assignment(driver2, "ASSISTANT", vehicle.id)
                else:
                    as_assistant[driver2] = dto
        return as_driver, as_assistant


def _log_duplicate_assignment(
    customer_number: str,
    role: str,
    vehicle_id: object,
) -> None:
    """Log duplicate current vehicle assignments hidden by the single-value API."""
    logger.warning(
        "Duplicate current vehicle assignment ignored",
        extra={
            "domain": "driver",
            "reader": "DjangoDriverVehicleAssignmentReader",
            "customer_number": customer_number,
            "assignment_role": role,
            "ignored_vehicle_id": str(vehicle_id),
        },
    )
