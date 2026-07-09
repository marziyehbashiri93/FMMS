"""Celery tasks for the SAP Integration domain.

Scheduled task: ``retry_failed_sap_transactions``

Runs periodically (configured via Celery Beat) to retry any SAP transactions
that are in FAILED status and still have remaining retry attempts.

The task is scaffolded here and will be fully wired to Celery in Milestone 6
when the async worker infrastructure is configured.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def retry_failed_sap_transactions() -> None:
    """Retry all eligible failed SAP transactions.

    Finds all ``SAPTransaction`` records with status FAILED where
    ``retry_count < max_retries`` and re-submits them via
    ``SAPTransactionManager.retry()``.

    This function is registered as a Celery task in Milestone 6.
    It is a plain Python function here so it can be unit tested
    without a running Celery worker.

    Note:
        Adapter call routing (mapping ``SAPObjectType`` to the correct
        adapter callable) will be implemented when Application Services
        are wired in Milestone 5.
    """
    logger.info(
        "SAP retry task triggered — wiring deferred to Milestone 6",
        extra={"domain": "integration"},
    )
