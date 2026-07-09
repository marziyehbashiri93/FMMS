"""Model-free serializers for procurement API v1."""

from __future__ import annotations

from rest_framework import serializers

from apps.procurement.domain.entities import POStatus, PRStatus


class PurchaseRequisitionCreateSerializer(serializers.Serializer):
    """Validate purchase requisition creation input."""

    repair_order_id = serializers.UUIDField()


class PRLineItemCreateSerializer(serializers.Serializer):
    """Validate PR line-item creation input."""

    material_number = serializers.CharField(max_length=18)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = serializers.CharField(max_length=10)
    description = serializers.CharField(max_length=500)
    estimated_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    currency = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class SubmitPRToSAPSerializer(serializers.Serializer):
    """Validate PR submission to SAP."""

    document_type = serializers.CharField(max_length=10)
    plant = serializers.CharField(max_length=10)
    delivery_date = serializers.DateField()
    idempotency_key = serializers.CharField(required=False, allow_null=True)
    header_text = serializers.CharField(
        required=False, allow_null=True, allow_blank=True
    )


class ReceivePOLineItemSerializer(serializers.Serializer):
    """Validate a PO line item received from SAP."""

    material_number = serializers.CharField(max_length=18)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = serializers.CharField(max_length=10)
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField(max_length=3)


class ReceivePOFromSAPSerializer(serializers.Serializer):
    """Validate purchase order receipt from SAP."""

    pr_id = serializers.UUIDField()
    sap_po_number = serializers.CharField(max_length=20)
    vendor_number = serializers.CharField(max_length=20)
    line_items = ReceivePOLineItemSerializer(many=True)


class PRLineItemResponseSerializer(serializers.Serializer):
    """Serialize PR line-item DTOs."""

    id = serializers.UUIDField()
    material_number = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3)
    unit_of_measure = serializers.CharField()
    description = serializers.CharField()
    estimated_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, allow_null=True
    )
    currency = serializers.CharField(allow_null=True)


class PurchaseRequisitionResponseSerializer(serializers.Serializer):
    """Serialize purchase requisition response DTOs."""

    id = serializers.UUIDField()
    repair_order_id = serializers.UUIDField()
    status = serializers.ChoiceField(choices=[item.value for item in PRStatus])
    requested_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    line_items = PRLineItemResponseSerializer(many=True)
    sap_pr_number = serializers.CharField(allow_null=True)
    approved_by_id = serializers.UUIDField(allow_null=True)
    sap_transaction_id = serializers.UUIDField(allow_null=True)
    sap_transaction_status = serializers.CharField(allow_null=True)


class PurchaseOrderResponseSerializer(serializers.Serializer):
    """Serialize purchase order response DTOs."""

    id = serializers.UUIDField()
    pr_id = serializers.UUIDField()
    vendor_number = serializers.CharField()
    status = serializers.ChoiceField(choices=[item.value for item in POStatus])
    created_by_id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    sap_po_number = serializers.CharField(allow_null=True)
    approved_by_id = serializers.UUIDField(allow_null=True)
