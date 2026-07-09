"""Celery task: retry failed SAP write transactions."""

from __future__ import annotations

from celery import shared_task

from infrastructure.messaging.task_logging import get_task_logger, task_log_extra

logger = get_task_logger("integration", __name__)
TASK_NAME = "retry_failed_sap_transactions"


@shared_task(bind=True, max_retries=3, name="fmms.retry_failed_sap_transactions")
def retry_failed_sap_transactions(
    self: object,
    correlation_id: str | None = None,
) -> dict[str, str]:
    """Retry eligible FAILED SAP transactions via the application facade.

    Args:
        self: Bound Celery task.
        correlation_id: Optional correlation id for log tracing.

    Returns:
        Status payload for Celery result backend.
    """
    from interfaces.api.v1 import deps

    extra = task_log_extra(
        self,  # type: ignore[arg-type]
        task_name=TASK_NAME,
        correlation_id=correlation_id,
    )
    logger.info("SAP retry task started", extra=extra)
    try:
        deps.get_retry_failed_sap_transactions_service().execute(
            request_id=str(extra["correlation_id"])
        )
    except Exception as exc:
        logger.exception(
            "SAP retry task failed",
            extra={**extra, "error": str(exc)},
        )
        raise
    logger.info("SAP retry task completed", extra={**extra, "result": "success"})
    return {"status": "ok", "task_name": TASK_NAME}
