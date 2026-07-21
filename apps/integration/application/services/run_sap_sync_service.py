"""Application service for running all SAP read synchronisations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from apps.inspection.application.services.sync_inspection_templates_from_sap_service import (
    SyncInspectionTemplatesFromSAPService,
)
from apps.vehicle.application.services.sync_vehicles_from_sap_service import (
    SyncVehiclesFromSAPService,
)
from core.logging.structured_logger import get_structured_logger

logger = get_structured_logger("integration", __name__)

SAP_SYNC_SUCCESS = "SUCCESS"
SAP_SYNC_FAILED = "FAILED"
SAP_SYNC_PARTIAL_SUCCESS = "PARTIAL_SUCCESS"


@dataclass(frozen=True)
class SAPSyncItemResultDTO:
    """Result of one SAP read synchronisation."""

    name: str
    status: str
    summary: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class RunSAPSyncResultDTO:
    """Result of the global SAP read synchronisation run."""

    status: str
    started_at: datetime
    finished_at: datetime
    items: list[SAPSyncItemResultDTO]


class RunSAPSyncService:
    """Run every currently supported SAP read sync in a single workflow.

    Args:
        vehicle_sync_service: Imports vehicle and driver master data from SAP.
        inspection_template_sync_service: Imports inspection templates from SAP.
    """

    def __init__(
        self,
        vehicle_sync_service: SyncVehiclesFromSAPService,
        inspection_template_sync_service: SyncInspectionTemplatesFromSAPService,
    ) -> None:
        self._vehicle_sync_service = vehicle_sync_service
        self._inspection_template_sync_service = inspection_template_sync_service

    def execute(self, *, request_id: str = "") -> RunSAPSyncResultDTO:
        """Run all SAP read syncs and return a per-sync status summary.

        Args:
            request_id: Correlation id for structured logging.

        Returns:
            A ``RunSAPSyncResultDTO`` containing global and item-level statuses.
        """
        started_at = datetime.now(tz=UTC)
        logger.info(
            "Running global SAP read sync",
            extra={
                "domain": "integration",
                "service": "RunSAPSyncService",
                "operation": "execute",
                "request_id": request_id,
            },
        )
        items = [
            self._run_item(
                name="vehicles",
                sync=lambda: self._vehicle_sync_service.execute(request_id=request_id),
            ),
            self._run_item(
                name="inspection_templates",
                sync=lambda: self._inspection_template_sync_service.execute(
                    request_id=request_id
                ),
            ),
        ]
        finished_at = datetime.now(tz=UTC)
        status = _global_status(items)
        logger.info(
            "Global SAP read sync completed",
            extra={
                "domain": "integration",
                "service": "RunSAPSyncService",
                "operation": "execute",
                "request_id": request_id,
                "result": status,
            },
        )
        return RunSAPSyncResultDTO(
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            items=items,
        )

    def _run_item(
        self,
        *,
        name: str,
        sync: Callable[[], object],
    ) -> SAPSyncItemResultDTO:
        """Run one sync and isolate its failure from the remaining syncs."""
        try:
            result = sync()
        except Exception as exc:  # noqa: BLE001 - global sync must continue.
            logger.error(
                "SAP read sync item failed",
                extra={
                    "domain": "integration",
                    "service": "RunSAPSyncService",
                    "operation": "_run_item",
                    "sync_name": name,
                    "exception": str(exc),
                },
                exc_info=True,
            )
            return SAPSyncItemResultDTO(
                name=name,
                status=SAP_SYNC_FAILED,
                summary={},
                error=str(exc),
            )
        return SAPSyncItemResultDTO(
            name=name,
            status=SAP_SYNC_SUCCESS,
            summary=asdict(result) if hasattr(result, "__dataclass_fields__") else {},
        )


def _global_status(items: list[SAPSyncItemResultDTO]) -> str:
    """Return the aggregate status for a global SAP sync run."""
    succeeded = sum(1 for item in items if item.status == SAP_SYNC_SUCCESS)
    if succeeded == len(items):
        return SAP_SYNC_SUCCESS
    if succeeded == 0:
        return SAP_SYNC_FAILED
    return SAP_SYNC_PARTIAL_SUCCESS
