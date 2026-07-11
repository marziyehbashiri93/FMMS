"""Vehicle handover API viewset."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.handover.application.dto.handover_dto import ConfirmVehicleHandoverDTO
from core.permissions import IsReadOnlyOrTechnicianOrAbove
from interfaces.api.v1 import deps
from interfaces.api.v1.handover.serializers import (
    VehicleHandoverConfirmSerializer,
    VehicleHandoverResponseSerializer,
)
from interfaces.api.v1.utils import request_id_from, user_id_from


class VehicleHandoverViewSet(GenericViewSet):
    """Expose vehicle handover services through REST endpoints."""

    permission_classes = [IsReadOnlyOrTechnicianOrAbove]

    @extend_schema(responses=VehicleHandoverResponseSerializer(many=True))
    def list(self, request: Request) -> Response:
        """List all vehicle handovers."""
        items = deps.get_list_vehicle_handovers_service().execute()
        return Response(VehicleHandoverResponseSerializer(items, many=True).data)

    @extend_schema(
        request=VehicleHandoverConfirmSerializer,
        responses=VehicleHandoverResponseSerializer,
    )
    @action(detail=True, methods=["post"])
    def confirm(self, request: Request, pk: str | None = None) -> Response:
        """Confirm driver handover result."""
        serializer = VehicleHandoverConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = deps.get_confirm_vehicle_handover_service().execute(
            ConfirmVehicleHandoverDTO(
                handover_id=uuid.UUID(str(pk)),
                accepted=serializer.validated_data["accepted"],
                comment=serializer.validated_data.get("comment"),
                request_id=request_id_from(request),
                confirmed_by=user_id_from(request),
            )
        )
        return Response(VehicleHandoverResponseSerializer(result).data)
