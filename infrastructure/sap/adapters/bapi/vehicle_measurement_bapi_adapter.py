"""Vehicle measurement document adapter for SAP odometer writes."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.measurement_document import (
    SAPMeasurementDocumentDTO,
    UpdateVehicleMeasurementRequest,
)
from core.sap.ports.measurement_document_port import ISAPMeasurementDocumentPort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_UPDATE_MEASUREMENT = "MEASUREM_DOCUM_RFC_SINGLE_001"


class VehicleMeasurementBAPIAdapter(ISAPMeasurementDocumentPort):
    """Write latest vehicle odometer values to SAP measurement documents."""

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def update_vehicle_odometer(
        self,
        request: UpdateVehicleMeasurementRequest,
    ) -> SAPMeasurementDocumentDTO:
        """Write a vehicle odometer reading linked to a PM notification."""
        params = self._build_update_params(request)
        logger.info(
            "Updating SAP vehicle odometer measurement",
            extra={
                "equipment_number": request.equipment_number,
                "notification_number": request.notification_number,
                "domain": "integration",
            },
        )
        try:
            result = self._client.bapi_call(_FM_UPDATE_MEASUREMENT, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure updating vehicle measurement: {exc}"
            ) from exc

        assert_bapi_success(result, context="Vehicle measurement update")
        document_number = _measurement_document_number_from_result(result)
        return SAPMeasurementDocumentDTO(
            measurement_document_number=document_number,
            equipment_number=request.equipment_number,
            notification_number=request.notification_number,
            odometer_km=request.odometer_km,
            created_at=datetime.now(tz=UTC),
        )

    @staticmethod
    def _build_update_params(
        request: UpdateVehicleMeasurementRequest,
    ) -> dict[str, Any]:
        """Build SAP import parameters from the measurement request."""
        return {
            "MEASUREMENT_POINT": {
                "IMRC_POINT": str(request.odometer_km),
                "IMRC_IDATE": request.recorded_at.strftime("%Y%m%d"),
                "IMRC_ITIME": request.recorded_at.strftime("%H%M%S"),
            },
            "Notification_Type": {
                "SHN_EQUIPMENT": request.equipment_number,
                "QMNUM": request.notification_number,
                "QMART": request.notification_type,
            },
        }


def _measurement_document_number_from_result(result: dict[str, Any]) -> str:
    """Extract a measurement document number from known SAP response shapes."""
    for key in ("MEASUREMENT_DOCUMENT", "MDOCM", "DOCUMENT_NUMBER"):
        value = result.get(key)
        if value:
            return str(value)
    return ""
