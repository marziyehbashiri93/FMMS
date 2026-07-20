"""Serializers for vehicle handover APIs."""

from __future__ import annotations

from rest_framework import serializers

from apps.handover.domain.entities import VehicleHandoverStatus


class VehicleHandoverConfirmSerializer(serializers.Serializer):
    """Validate handover confirmation payload.

    External repairs require invoice fields when ``accepted`` is true. Validation
    of that business rule happens in the application service after loading the
    repair order workshop type.
    """

    accepted = serializers.BooleanField()
    comment = serializers.CharField(
        max_length=500, required=False, allow_null=True, allow_blank=True
    )
    invoice_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    invoice_currency = serializers.CharField(
        max_length=8, required=False, allow_null=True, allow_blank=True
    )
    invoice_vendor_id = serializers.CharField(
        max_length=64, required=False, allow_null=True, allow_blank=True
    )
    invoice_document = serializers.CharField(
        max_length=1024, required=False, allow_null=True, allow_blank=True
    )


class VehicleHandoverResponseSerializer(serializers.Serializer):
    """Serialize handover response DTO."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    vehicle_id = serializers.UUIDField()
    status = serializers.ChoiceField(
        choices=[item.value for item in VehicleHandoverStatus]
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    comment = serializers.CharField(allow_null=True)
    driver_id = serializers.UUIDField(allow_null=True, required=False)
    confirmed_at = serializers.DateTimeField(allow_null=True, required=False)
