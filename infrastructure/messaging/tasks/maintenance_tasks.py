"""Celery task: trigger overdue preventive-maintenance work orders."""

from __future__ import annotations

from celery import shared_task

from infrastructure.messaging.task_logging import get_task_logger, task_log_extra

logger = get_task_logger("pm", __name__)
TASK_NAME = "trigger_overdue_pm_work_orders"


@shared_task(bind=True, max_retries=3, name="fmms.trigger_overdue_pm_work_orders")
def trigger_overdue_pm_work_orders(
    self: object,
    correlation_id: str | None = None,
    create_sap_notification: bool = False,
) -> dict[str, object]:
    """Trigger PM work orders for overdue active plans.

    Args:
        self: Bound Celery task.
        correlation_id: Optional correlation id for log tracing.
        create_sap_notification: Forwarded to the application service.

    Returns:
        Status payload including triggered count.
    """
    from interfaces.api.v1 import deps

    extra = task_log_extra(
        self,  # type: ignore[arg-type]
        task_name=TASK_NAME,
        correlation_id=correlation_id,
    )
    logger.info("Overdue PM trigger task started", extra=extra)
    try:
        results = deps.get_trigger_overdue_pm_work_orders_service().execute(
            request_id=str(extra["correlation_id"]),
            create_sap_notification=create_sap_notification,
        )
    except Exception as exc:
        logger.exception(
            "Overdue PM trigger task failed",
            extra={**extra, "error": str(exc)},
        )
        raise
    logger.info(
        "Overdue PM trigger task completed",
        extra={**extra, "result": "success", "count": len(results)},
    )
    return {"status": "ok", "task_name": TASK_NAME, "count": len(results)}
