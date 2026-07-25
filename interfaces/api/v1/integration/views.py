"""Thin integration REST API view set (read-only SAP transactions)."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.integration.domain.entities import SAPObjectType, SAPTransactionStatus
from core.permissions import IsFMMSAuthenticated, IsSupervisorOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.integration.serializers import (
    SAPSyncRunHistorySerializer,
    SAPSyncRunResponseSerializer,
    SAPTransactionResponseSerializer,
    SAPTransactionSummarySerializer,
)
from interfaces.api.v1.schema_tags import API_TAGS
from interfaces.api.v1.utils import paginate_dto_list, request_id_from, user_id_from


class SAPTransactionViewSet(GenericViewSet):
    """Expose SAP transaction records as a read-only API."""

    permission_classes = [IsFMMSAuthenticated]

    @extend_schema(
        tags=[API_TAGS.integration], responses=SAPTransactionResponseSerializer
    )
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one SAP transaction by id."""
        repo = deps.get_sap_transaction_repository()
        entity = repo.get_by_id(uuid.UUID(str(pk)))
        return Response(SAPTransactionResponseSerializer(entity).data)

    @extend_schema(
        tags=[API_TAGS.integration],
        responses=SAPTransactionResponseSerializer(many=True),
    )
    def list(self, request: Request) -> Response:
        """List SAP transactions, optionally filtered by status/object_type."""
        repo = deps.get_sap_transaction_repository()
        status_raw = request.query_params.get("status")
        object_type_raw = request.query_params.get("object_type")
        if status_raw:
            items = repo.list_by_status(SAPTransactionStatus(status_raw))
        else:
            items = []
            for txn_status in SAPTransactionStatus:
                items.extend(repo.list_by_status(txn_status))
        if object_type_raw:
            object_type = SAPObjectType(object_type_raw)
            items = [item for item in items if item.object_type == object_type]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = paginate_dto_list(self, items)
        serializer = SAPTransactionResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @extend_schema(
        tags=[API_TAGS.integration],
        responses=SAPTransactionSummarySerializer,
    )
    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request: Request) -> Response:
        """Return aggregate SAP transaction counts for dashboard cards."""
        del request
        repo = deps.get_sap_transaction_repository()
        by_status: dict[SAPTransactionStatus, int] = {}
        last_created_at = None
        total = 0
        for txn_status in SAPTransactionStatus:
            items = repo.list_by_status(txn_status)
            by_status[txn_status] = len(items)
            total += len(items)
            for item in items:
                if last_created_at is None or item.created_at > last_created_at:
                    last_created_at = item.created_at
        payload = {
            "total": total,
            "success": by_status.get(SAPTransactionStatus.SUCCESS, 0),
            "failed": by_status.get(SAPTransactionStatus.FAILED, 0)
            + by_status.get(SAPTransactionStatus.RETRYING, 0),
            "pending": by_status.get(SAPTransactionStatus.PENDING, 0)
            + by_status.get(SAPTransactionStatus.IN_PROGRESS, 0),
            "exhausted": by_status.get(SAPTransactionStatus.EXHAUSTED, 0),
            "last_created_at": last_created_at,
        }
        return Response(SAPTransactionSummarySerializer(payload).data)


class SAPSyncViewSet(GenericViewSet):
    """Expose a single API for running all SAP read synchronisations."""

    permission_classes = [IsSupervisorOrAbove]

    @extend_schema(
        tags=[API_TAGS.integration],
        request=None,
        responses=SAPSyncRunResponseSerializer,
    )
    def create(self, request: Request) -> Response:
        """Run every supported SAP read sync."""
        result = deps.get_run_sap_sync_service().execute(
            request_id=request_id_from(request),
            trigger_source="API",
            triggered_by=user_id_from(request),
        )
        return Response(SAPSyncRunResponseSerializer(result).data)

    @extend_schema(
        tags=[API_TAGS.integration],
        responses=SAPSyncRunHistorySerializer(many=True),
    )
    @action(detail=False, methods=["get"], url_path="history")
    def history(self, request: Request) -> Response:
        """List persisted SAP read-sync runs."""
        items = deps.get_list_sap_sync_runs_service().execute()
        page = paginate_dto_list(self, items)
        serializer = SAPSyncRunHistorySerializer(
            page if page is not None else items, many=True
        )
        return (
            self.get_paginated_response(serializer.data)
            if page is not None
            else Response(serializer.data)
        )
