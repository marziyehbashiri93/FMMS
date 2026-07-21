"""Model-free serializers for vehicle API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.vehicle.domain.entities import VehicleStatus


class VehicleAssignedDriverSerializer(serializers.Serializer):
    """Serialize assigned driver details in vehicle responses."""

    customer_number = serializers.CharField()
    name = serializers.CharField(allow_null=True)


class VehicleResponseSerializer(serializers.Serializer):
    """Serialize application vehicle response DTOs."""

    id = serializers.UUIDField()
    vehicle_number = serializers.CharField()
    license_plate = serializers.CharField()
    status = serializers.ChoiceField(choices=[item.value for item in VehicleStatus])
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
    odometer_km = serializers.IntegerField(min_value=0)
    source = serializers.CharField(max_length=30, required=False, default="DRIVER")


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
        choices=[
            status.value
            for status in VehicleStatus
            if status != VehicleStatus.DECOMMISSIONED
        ]
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
