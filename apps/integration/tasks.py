"""Deprecated stub — Celery tasks live under ``infrastructure.messaging.tasks``.

Kept as a module so historical imports fail loudly with a clear message.
"""

from __future__ import annotations

raise ImportError(
    "apps.integration.tasks is retired. Use "
    "infrastructure.messaging.tasks.sap_retry_tasks.retry_failed_sap_transactions."
)
