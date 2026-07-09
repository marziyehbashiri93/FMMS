"""
FMMS Structured Logger Factory.

Provides a centralized logger factory that pre-binds domain context
to every log record, ensuring consistent structured output.

Usage:
    logger = get_structured_logger(domain="vehicle", module=__name__)
    logger.info("Vehicle created", extra={"vehicle_id": str(vehicle.id)})
"""

import logging
from collections.abc import MutableMapping
from typing import Any


class FMMSLoggerAdapter(logging.LoggerAdapter):  # type: ignore[type-arg]
    """
    Logger adapter that injects FMMS-specific context into every log record.

    Pre-binds 'domain' so the JSON formatter can include it in every record
    without callers needing to pass it explicitly.
    """

    def process(
        self,
        msg: str,
        kwargs: MutableMapping[str, Any],
    ) -> tuple[str, MutableMapping[str, Any]]:
        """
        Inject domain and other bound context into the log record.

        Args:
            msg: The log message.
            kwargs: Keyword arguments passed to the logging call.

        Returns:
            A tuple of (message, updated kwargs) with extra context injected.
        """
        extra = kwargs.get("extra", {})
        domain = (self.extra or {}).get("domain", "core")
        extra.setdefault("domain", domain)
        kwargs["extra"] = extra
        return msg, kwargs


def get_structured_logger(domain: str, module: str) -> FMMSLoggerAdapter:
    """
    Create a structured logger pre-bound to an FMMS domain.

    The returned logger emits records under the 'fmms.<domain>.<module>'
    namespace and automatically injects the domain into every record.

    Args:
        domain: The FMMS domain identifier. Must be one of:
                vehicle, driver, inspection, fault, repair, pm,
                procurement, integration, authentication, security, core.
        module: The Python module name (__name__ of the calling module).

    Returns:
        A FMMSLoggerAdapter bound to the specified domain and module.

    Example:
        logger = get_structured_logger(domain="vehicle", module=__name__)
        logger.info("Vehicle created", extra={"vehicle_id": "abc-123"})
    """
    logger_name = f"fmms.{domain}.{module}"
    base_logger = logging.getLogger(logger_name)
    return FMMSLoggerAdapter(base_logger, extra={"domain": domain})
