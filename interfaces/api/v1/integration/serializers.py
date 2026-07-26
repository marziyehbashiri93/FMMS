"""Model-free serializers for integration API v1."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.integration.domain.entities import SAPObjectType, SAPTransactionStatus

# Human-readable FMMS section for each SAP object type (write audit trail).
_OBJECT_TYPE_SECTIONS: dict[str, str] = {
    SAPObjectType.VEHICLE.value: "خودرو",
    SAPObjectType.FAULT.value: "خرابی / اعلان PM",
    SAPObjectType.REPAIR_ORDER.value: "تعمیر / سفارش کار",
    SAPObjectType.PM_WORK_ORDER.value: "نگهداری پیشگیرانه",
    SAPObjectType.MEASUREMENT_DOCUMENT.value: "کیلومترشمار",
    SAPObjectType.VEHICLE_ASSIGNMENT.value: "تخصیص خودرو جایگزین",
    SAPObjectType.PURCHASE_REQUISITION.value: "تدارکات / درخواست خرید",
    SAPObjectType.PURCHASE_ORDER.value: "تدارکات / سفارش خرید",
    SAPObjectType.GOODS_RECEIPT.value: "انبار / رسید کالا",
    SAPObjectType.GOODS_ISSUE.value: "انبار / صدور کالا",
}


class SAPTransactionResponseSerializer(serializers.Serializer):
    """Serialize SAP transaction domain entities for read APIs."""

    id = serializers.UUIDField()
    object_type = serializers.ChoiceField(
        choices=[item.value for item in SAPObjectType]
    )
    section = serializers.SerializerMethodField()
    protocol = serializers.SerializerMethodField()
    object_id = serializers.UUIDField()
    idempotency_key = serializers.CharField()
    status = serializers.ChoiceField(
        choices=[item.value for item in SAPTransactionStatus]
    )
    retry_count = serializers.IntegerField()
    max_retries = serializers.IntegerField()
    request_payload = serializers.DictField()
    response_payload = serializers.DictField(allow_null=True)
    sap_document_number = serializers.CharField(allow_null=True)
    error_message = serializers.CharField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    completed_at = serializers.DateTimeField(allow_null=True)

    def get_section(self, obj: Any) -> str:
        """Return Persian section label for the business object type."""
        object_type = getattr(obj, "object_type", None)
        key = object_type.value if hasattr(object_type, "value") else str(object_type)
        return _OBJECT_TYPE_SECTIONS.get(key, key)

    def get_protocol(self, obj: Any) -> str:
        """Write transactions are recorded through the BAPI manager path."""
        del obj
        return "BAPI"


class SAPTransactionSummarySerializer(serializers.Serializer):
    """Aggregate counts for dashboard SAP log cards."""

    total = serializers.IntegerField()
    success = serializers.IntegerField()
    failed = serializers.IntegerField()
    pending = serializers.IntegerField()
    exhausted = serializers.IntegerField()
    last_created_at = serializers.DateTimeField(allow_null=True)


class SAPSyncItemResultSerializer(serializers.Serializer):
    """Serialize the result of one SAP read-sync item."""

    name = serializers.CharField()
    status = serializers.ChoiceField(choices=["SUCCESS", "FAILED", "PARTIAL_SUCCESS"])
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()
    summary = serializers.DictField()
    error = serializers.CharField(allow_null=True)


class SAPSyncRunResponseSerializer(serializers.Serializer):
    """Serialize the global SAP read-sync run result."""

    id = serializers.CharField()
    trigger_source = serializers.ChoiceField(choices=["API", "CELERY", "JOB"])
    status = serializers.ChoiceField(choices=["SUCCESS", "FAILED", "PARTIAL_SUCCESS"])
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField()
    items = SAPSyncItemResultSerializer(many=True)


class SAPSyncRunHistorySerializer(serializers.Serializer):
    """Serialize a persisted SAP read-sync run."""

    id = serializers.CharField()
    trigger_source = serializers.ChoiceField(choices=["API", "CELERY", "JOB"])
    status = serializers.ChoiceField(
        choices=["IN_PROGRESS", "SUCCESS", "FAILED", "PARTIAL_SUCCESS"]
    )
    request_id = serializers.CharField()
    triggered_by = serializers.CharField(allow_null=True)
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    summary = serializers.DictField()
    error = serializers.CharField(allow_null=True)
    items = SAPSyncItemResultSerializer(many=True)
