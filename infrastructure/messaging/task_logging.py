"""Shared helpers for Celery task structured logging."""

from __future__ import annotations

import uuid
from typing import Any

from celery import Task

from core.logging.structured_logger import FMMSLoggerAdapter, get_structured_logger


def task_log_extra(
    task: Task,
    *,
    task_name: str,
    correlation_id: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build the mandatory structured log fields for a Celery task.

    Args:
        task: Bound Celery task instance.
        task_name: Stable task name for log correlation.
        correlation_id: Optional caller-supplied correlation id.
        **extra: Additional structured fields.

    Returns:
        Dict suitable for ``logger.info(..., extra=...)``.
    """
    resolved_correlation = correlation_id or str(uuid.uuid4())
    payload: dict[str, Any] = {
        "task_name": task_name,
        "task_id": str(getattr(task.request, "id", "") or ""),
        "correlation_id": resolved_correlation,
    }
    payload.update(extra)
    return payload


def get_task_logger(domain: str, module: str) -> FMMSLoggerAdapter:
    """Return a structured logger for messaging tasks.

    Args:
        domain: FMMS domain (``integration`` or ``pm``).
        module: Calling module ``__name__``.

    Returns:
        Structured logger adapter.
    """
    return get_structured_logger(domain, module)
