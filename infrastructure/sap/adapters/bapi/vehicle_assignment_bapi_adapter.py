"""SAP adapter for replacement vehicle assignment requests."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError
from core.sap.dtos.vehicle_assignment import (
    RequestReplacementVehicleAssignmentRequest,
    SAPVehicleAssignmentRequestDTO,
)
from core.sap.ports.vehicle_assignment_port import ISAPVehicleAssignmentPort
from infrastructure.sap.adapters.bapi._bapi_helper import assert_bapi_success
from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)

_FM_REQUEST_REPLACEMENT_ASSIGNMENT = "ZFM_FLEET_ASSIGN_REPLACEMENT"


class VehicleAssignmentBAPIAdapter(ISAPVehicleAssignmentPort):
    """Request a replacement vehicle assignment from SAP.

    The concrete SAP function module name is a placeholder until the SAP team
    provides the final write API. The application layer depends on the port, so
    this adapter can be swapped for the final OData/BAPI implementation.
    """

    def __init__(self, client: ISAPClient) -> None:
        self._client = client

    def request_replacement_assignment(
        self,
        request: RequestReplacementVehicleAssignmentRequest,
    ) -> SAPVehicleAssignmentRequestDTO:
        """Ask SAP to assign a replacement vehicle to the driver."""
        params = self._build_params(request)
        logger.info(
            "Requesting SAP replacement vehicle assignment",
            extra={
                "driver_customer_number": request.driver_customer_number,
                "unavailable_vehicle_number": request.unavailable_vehicle_number,
                "domain": "integration",
            },
        )
        try:
            result = self._client.bapi_call(_FM_REQUEST_REPLACEMENT_ASSIGNMENT, params)
        except SAPClientError as exc:
            raise SAPIntegrationError(
                f"Transport failure requesting replacement vehicle assignment: {exc}"
            ) from exc

        assert_bapi_success(result, context="Replacement vehicle assignment")
        return SAPVehicleAssignmentRequestDTO(
            assignment_request_number=str(result.get("ASSIGNMENT_REQUEST_NO", "")),
            driver_customer_number=request.driver_customer_number,
            unavailable_vehicle_number=request.unavailable_vehicle_number,
            created_at=datetime.now(tz=UTC),
        )

    @staticmethod
    def _build_params(
        request: RequestReplacementVehicleAssignmentRequest,
    ) -> dict[str, Any]:
        """Build SAP parameters for the replacement assignment request."""
        return {
            "DRIVER_CUSTOMER_NUMBER": request.driver_customer_number,
            "UNAVAILABLE_VEHICLE": request.unavailable_vehicle_number,
            "FAULT_ID": request.fault_id,
            "REQUEST_DATE": request.requested_at.strftime("%Y%m%d"),
            "REQUEST_TIME": request.requested_at.strftime("%H%M%S"),
            "REASON": request.reason[:220],
        }
