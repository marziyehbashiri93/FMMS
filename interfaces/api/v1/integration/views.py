"""Thin integration REST API view set (read-only SAP transactions)."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.integration.domain.entities import SAPTransactionStatus
from core.permissions import IsFMMSAuthenticated
from interfaces.api.v1 import deps
from interfaces.api.v1.integration.serializers import SAPTransactionResponseSerializer
from interfaces.api.v1.utils import paginate_dto_list


class SAPTransactionViewSet(GenericViewSet):
    """Expose SAP transaction records as a read-only API."""

    permission_classes = [IsFMMSAuthenticated]

    @extend_schema(responses=SAPTransactionResponseSerializer)
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        """Retrieve one SAP transaction by id."""
        repo = deps.get_sap_transaction_repository()
        entity = repo.get_by_id(uuid.UUID(str(pk)))
        return Response(SAPTransactionResponseSerializer(entity).data)

    @extend_schema(responses=SAPTransactionResponseSerializer(many=True))
    def list(self, request: Request) -> Response:
        """List SAP transactions, optionally filtered by status."""
        repo = deps.get_sap_transaction_repository()
        status_raw = request.query_params.get("status")
        if status_raw:
            items = repo.list_by_status(SAPTransactionStatus(status_raw))
        else:
            items = []
            for txn_status in SAPTransactionStatus:
                items.extend(repo.list_by_status(txn_status))
        page = paginate_dto_list(self, items)
        serializer = SAPTransactionResponseSerializer(
            page if page is not None else items, many=True
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)
