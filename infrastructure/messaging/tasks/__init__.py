"""Celery task package for FMMS background jobs.

Tasks are thin orchestrators: resolve deps → call application services → log.
"""

from infrastructure.messaging.tasks.maintenance_tasks import (
    trigger_overdue_pm_work_orders,
)
from infrastructure.messaging.tasks.sap_retry_tasks import retry_failed_sap_transactions
from infrastructure.messaging.tasks.sap_sync_tasks import (
    sync_vehicles_from_sap,
)

__all__ = [
    "retry_failed_sap_transactions",
    "trigger_overdue_pm_work_orders",
    "sync_vehicles_from_sap",
]
