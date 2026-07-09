"""Shared BAPI response validation utilities.

Used internally by all BAPI adapters. Not part of the public API.
"""

from __future__ import annotations

from typing import Any

from apps.integration.domain.exceptions import SAPIntegrationError


def assert_bapi_success(
    result: dict[str, Any],
    context: str,
) -> None:
    """Validate the RETURN table of a BAPI result and raise on error.

    SAP BAPI functions communicate success/failure through a RETURN table.
    A message with ``TYPE='E'`` or ``TYPE='A'`` indicates an error.

    Args:
        result: The raw BAPI result dictionary containing a ``RETURN`` key.
        context: A human-readable context label for error messages.

    Raises:
        SAPIntegrationError: If the RETURN table contains an error or abort message.
    """
    return_table: list[dict[str, Any]] = result.get("RETURN", [])
    for entry in return_table:
        msg_type = entry.get("TYPE", "")
        if msg_type in ("E", "A"):
            sap_message = entry.get("MESSAGE", "Unknown SAP error")
            sap_id = entry.get("ID", "")
            sap_number = entry.get("NUMBER", "")
            raise SAPIntegrationError(
                f"{context}: SAP error [{sap_id}/{sap_number}] — {sap_message}",
                sap_error_code=f"{sap_id}/{sap_number}",
            )
