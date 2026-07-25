"""Model-free serializers for vehicle API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.vehicle.application.services.record_odometer_service import (
    _MAX_ODOMETER_KM,
    VehicleOdometerSource,
)
from apps.vehicle.domain.entities import VehicleStatus

VEHICLE_STATUS_CHOICES = [item.value for item in VehicleStatus]
MANUAL_VEHICLE_STATUS_CHOICES = [
    VehicleStatus.ACTIVE.value,
    VehicleStatus.INACTIVE.value,
    VehicleStatus.UNDER_REPAIR.value,
    VehicleStatus.SUSPENDED.value,
    VehicleStatus.OUT_OF_SERVICE.value,
]
VEHICLE_ORDERING_CHOICES = [
    "vehicle_number",
    "-vehicle_number",
    "license_plate",
    "-license_plate",
    "status",
    "-status",
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
    "commissioning_date",
    "-commissioning_date",
]


class VehicleComponentHistoryResponseSerializer(serializers.Serializer):
    """Serialize installed vehicle component history rows."""

    id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    component_type = serializers.CharField()
    material_number = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = serializers.CharField()
    description = serializers.CharField()
    installed_at = serializers.DateTimeField()
    recorded_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class VehicleAssignedDriverSerializer(serializers.Serializer):
    """Serialize assigned driver details in vehicle responses."""

    id = serializers.UUIDField(allow_null=True)
    customer_number = serializers.CharField()
    name = serializers.CharField(allow_null=True)


class VehicleResponseSerializer(serializers.Serializer):
    """Serialize application vehicle response DTOs."""

    id = serializers.UUIDField()
    vehicle_number = serializers.CharField()
    license_plate = serializers.CharField()
    status = serializers.ChoiceField(choices=VEHICLE_STATUS_CHOICES)
    status_label = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    commissioning_date = serializers.CharField(allow_null=True)
    driver1 = VehicleAssignedDriverSerializer(allow_null=True)
    driver2 = VehicleAssignedDriverSerializer(allow_null=True)


class VehicleSummarySerializer(serializers.Serializer):
    """Serialize vehicle dashboard summary values."""

    active_fleet_count = serializers.IntegerField()
    operational_fleet_count = serializers.IntegerField()
    under_repair_fleet_count = serializers.IntegerField()
    unusable_fleet_count = serializers.IntegerField()
    last_sap_sync_at = serializers.DateTimeField(allow_null=True)
    average_odometer_km = serializers.FloatField()
    average_faults_last_30_days = serializers.FloatField()


class VehicleOdometerRecordSerializer(serializers.Serializer):
    """Validate a daily odometer reading."""

    reading_date = serializers.DateField()
    odometer_km = serializers.IntegerField(min_value=0, max_value=_MAX_ODOMETER_KM)
    source = serializers.ChoiceField(
        choices=[item.value for item in VehicleOdometerSource],
        required=False,
        default=VehicleOdometerSource.DRIVER.value,
    )


class VehicleListQuerySerializer(serializers.Serializer):
    """Validate vehicle list query parameters."""

    status = serializers.ChoiceField(choices=VEHICLE_STATUS_CHOICES, required=False)
    ordering = serializers.ChoiceField(
        choices=VEHICLE_ORDERING_CHOICES,
        required=False,
        allow_blank=True,
    )
    search = serializers.CharField(required=False, allow_blank=True, max_length=100)


class DateRangeFilterSerializer(serializers.Serializer):
    """Validate optional from/to date query parameters."""

    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        """Ensure the date range is chronologically valid."""
        from_date = attrs.get("from_date")
        to_date = attrs.get("to_date")
        if from_date and to_date and from_date > to_date:
            raise serializers.ValidationError(
                {"to_date": "to_date must be greater than or equal to from_date."}
            )
        return attrs


class VehicleStatusChangeSerializer(serializers.Serializer):
    """Validate a vehicle status change requested from FMMS."""

    status = serializers.ChoiceField(
        choices=MANUAL_VEHICLE_STATUS_CHOICES
    )


class VehicleOdometerResponseSerializer(serializers.Serializer):
    """Serialize vehicle odometer history entries."""

    id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    reading_date = serializers.DateField()
    odometer_km = serializers.IntegerField()
    source = serializers.CharField()
    recorded_by = serializers.UUIDField()
    recorded_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class VehicleDriverAssignmentHistoryResponseSerializer(serializers.Serializer):
    """Serialize SAP driver-assignment history snapshots."""

    id = serializers.UUIDField()
    sync_run_id = serializers.UUIDField()
    request_id = serializers.CharField()
    synced_at = serializers.DateTimeField()
    vehicle_id = serializers.UUIDField()
    vehicle_number = serializers.CharField()
    license_plate = serializers.CharField()
    driver_role = serializers.ChoiceField(choices=["DRIVER", "ASSISTANT"])
    driver_customer_number = serializers.CharField(allow_null=True)


class VehicleDriverAssignmentSnapshotResponseSerializer(serializers.Serializer):
    """Serialize grouped driver-assignment snapshots for one vehicle."""

    assigned_at = serializers.DateTimeField()
    driver1 = VehicleAssignedDriverSerializer(allow_null=True)
    driver2 = VehicleAssignedDriverSerializer(allow_null=True)
