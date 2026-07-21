"""Celery tasks for vehicle synchronization from SAP OData master data."""

from __future__ import annotations

from celery import shared_task

from infrastructure.messaging.task_logging import get_task_logger, task_log_extra

logger = get_task_logger("integration", __name__)
BULK_TASK_NAME = "sync_vehicles_from_sap"


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
