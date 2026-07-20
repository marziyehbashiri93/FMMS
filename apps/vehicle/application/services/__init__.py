"""Vehicle application services — orchestration without business rules."""

from apps.vehicle.application.services.deactivate_vehicle_service import (
    DeactivateVehicleService,
)
from apps.vehicle.application.services.get_vehicle_service import (
    GetVehicleService,
    ListVehiclesService,
)
from apps.vehicle.application.services.record_odometer_service import (
    ListVehicleOdometerHistoryService,
    RecordVehicleOdometerService,
)
from apps.vehicle.application.services.sync_sap_equipment_service import (
    SyncSAPEquipmentService,
)
from apps.vehicle.application.services.update_vehicle_service import (
    UpdateVehicleService,
)

__all__ = [
    "UpdateVehicleService",
    "DeactivateVehicleService",
    "GetVehicleService",
    "ListVehiclesService",
    "ListVehicleOdometerHistoryService",
    "RecordVehicleOdometerService",
    "SyncSAPEquipmentService",
]
