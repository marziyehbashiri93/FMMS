"""Celery task: synchronize a single vehicle from SAP equipment master."""

from __future__ import annotations

from celery import shared_task

from infrastructure.messaging.task_logging import get_task_logger, task_log_extra

logger = get_task_logger("integration", __name__)
TASK_NAME = "sync_equipment_from_sap"


@shared_task(bind=True, max_retries=3, name="fmms.sync_equipment_from_sap")
def sync_equipment_from_sap(
    self: object,
    sap_equipment_number: str,
    correlation_id: str | None = None,
) -> dict[str, str]:
    """Sync one fleet vehicle from a SAP equipment number.

    This is a single-equipment sync only — not a bulk fleet sync.

    Args:
        self: Bound Celery task.
        sap_equipment_number: SAP PM equipment number to synchronize.
        correlation_id: Optional correlation id for log tracing.

    Returns:
        Status payload with the equipment number processed.
    """
    from interfaces.api.v1 import deps

    extra = task_log_extra(
        self,  # type: ignore[arg-type]
        task_name=TASK_NAME,
        correlation_id=correlation_id,
        sap_equipment_number=sap_equipment_number,
    )
    logger.info("Single equipment SAP sync started", extra=extra)
    try:
        deps.get_sync_sap_equipment_service().execute(
            sap_equipment_number,
            request_id=str(extra["correlation_id"]),
        )
    except Exception as exc:
        logger.exception(
            "Single equipment SAP sync failed",
            extra={**extra, "error": str(exc)},
        )
        raise
    logger.info(
        "Single equipment SAP sync completed",
        extra={**extra, "result": "success"},
    )
    return {
        "status": "ok",
        "task_name": TASK_NAME,
        "sap_equipment_number": sap_equipment_number,
    }
