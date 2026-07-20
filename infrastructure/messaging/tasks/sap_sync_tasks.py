"""Celery tasks for vehicle synchronization from SAP OData master data."""

from __future__ import annotations

from celery import shared_task

from infrastructure.messaging.task_logging import get_task_logger, task_log_extra

logger = get_task_logger("integration", __name__)
TASK_NAME = "sync_equipment_from_sap"
BULK_TASK_NAME = "sync_vehicles_from_sap"


@shared_task(bind=True, max_retries=3, name="fmms.sync_equipment_from_sap")
def sync_equipment_from_sap(
    self: object,
    vehicle_number: str,
    correlation_id: str | None = None,
) -> dict[str, str]:
    """Sync one fleet vehicle from a SAP VehicleNumber.

    This is a single-vehicle sync only — not a bulk fleet sync.

    Args:
        self: Bound Celery task.
        vehicle_number: SAP VehicleNumber to synchronize.
        correlation_id: Optional correlation id for log tracing.

    Returns:
        Status payload with the vehicle number processed.
    """
    from interfaces.api.v1 import deps

    extra = task_log_extra(
        self,  # type: ignore[arg-type]
        task_name=TASK_NAME,
        correlation_id=correlation_id,
        vehicle_number=vehicle_number,
    )
    logger.info("Single vehicle SAP sync started", extra=extra)
    try:
        deps.get_sync_sap_equipment_service().execute(
            vehicle_number,
            request_id=str(extra["correlation_id"]),
        )
    except Exception as exc:
        logger.exception(
            "Single vehicle SAP sync failed",
            extra={**extra, "error": str(exc)},
        )
        raise
    logger.info(
        "Single vehicle SAP sync completed",
        extra={**extra, "result": "success"},
    )
    return {
        "status": "ok",
        "task_name": TASK_NAME,
        "vehicle_number": vehicle_number,
    }


@shared_task(bind=True, max_retries=3, name="fmms.sync_vehicles_from_sap")
def sync_vehicles_from_sap(
    self: object,
    correlation_id: str | None = None,
) -> dict[str, int | str]:
    """Bulk sync FMMS vehicles from SAP through the OData equipment port."""
    from interfaces.api.v1 import deps

    extra = task_log_extra(
        self,  # type: ignore[arg-type]
        task_name=BULK_TASK_NAME,
        correlation_id=correlation_id,
    )
    logger.info("Bulk vehicle SAP sync started", extra=extra)
    try:
        result = deps.get_sync_vehicles_from_sap_service().execute(
            request_id=str(extra["correlation_id"]),
        )
    except Exception as exc:
        logger.exception(
            "Bulk vehicle SAP sync failed",
            extra={**extra, "error": str(exc)},
        )
        raise
    logger.info("Bulk vehicle SAP sync completed", extra={**extra, "result": "success"})
    return {
        "status": "ok",
        "task_name": BULK_TASK_NAME,
        "total_received": result.total_received,
        "created": result.created,
        "updated": result.updated,
        "decommissioned": result.decommissioned,
        "failed": result.failed,
    }
