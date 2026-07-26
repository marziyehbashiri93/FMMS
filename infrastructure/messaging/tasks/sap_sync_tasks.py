"""Celery tasks for SAP OData read synchronisation."""

from __future__ import annotations

from celery import shared_task

from infrastructure.messaging.task_logging import get_task_logger, task_log_extra

logger = get_task_logger("integration", __name__)
BULK_TASK_NAME = "sync_vehicles_from_sap"


@shared_task(bind=True, max_retries=3, name="fmms.sync_vehicles_from_sap")
def sync_vehicles_from_sap(
    self: object,
    correlation_id: str | None = None,
) -> dict[str, object]:
    """Run the global SAP read sync from a scheduled/background task."""
    from interfaces.api.v1 import deps

    extra = task_log_extra(
        self,  # type: ignore[arg-type]
        task_name=BULK_TASK_NAME,
        correlation_id=correlation_id,
    )
    logger.info("Bulk SAP read sync started", extra=extra)
    try:
        result = deps.get_run_sap_sync_service().execute(
            request_id=str(extra["correlation_id"]),
            trigger_source="CELERY",
        )
    except Exception as exc:
        logger.exception(
            "Bulk SAP read sync failed",
            extra={**extra, "error": str(exc)},
        )
        raise
    logger.info(
        "Bulk SAP read sync completed",
        extra={**extra, "result": result.status},
    )
    return {
        "status": "ok",
        "task_name": BULK_TASK_NAME,
        "sync_run_id": result.id,
        "sync_status": result.status,
        "items": [item.name for item in result.items],
    }
