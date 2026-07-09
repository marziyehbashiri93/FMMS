"""ISAPClient — transport-level abstraction for all SAP communication.

All concrete SAP clients (OData, BAPI, Mock) implement this ABC.
Adapters depend only on ``ISAPClient``; the concrete client is injected
at construction time, enabling seamless swap between mock and production.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class SAPClientError(Exception):
    """Raised by SAP clients on transport-level failures.

    This is a low-level exception representing communication problems
    (network timeout, authentication failure, unexpected HTTP status, etc.).
    Adapters catch ``SAPClientError`` and re-raise as ``SAPIntegrationError``
    from ``apps.integration.domain.exceptions``.

    Args:
        message: Human-readable description of the failure.
        status_code: Optional HTTP status code (for OData clients).
        raw_response: Optional raw response body for diagnostics.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        raw_response: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.raw_response = raw_response


class ISAPClient(ABC):
    """Transport-level contract for SAP communication.

    Adapters receive an ``ISAPClient`` instance by constructor injection.
    This contract defines the minimal surface area needed to support both
    OData (read) and BAPI/RFC (write) operations without leaking
    protocol details into adapters.

    All methods raise ``SAPClientError`` on transport failures.
    Adapters are responsible for translating these into domain exceptions.
    """

    @abstractmethod
    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GET request against an OData service entity.

        Args:
            service: The OData service name (e.g. ``"API_EQUIPMENT"``)
            entity: The entity set or entity key expression
                (e.g. ``"EquipmentSet"`` or ``"Equipment('10000001')"``)
            params: Optional OData query parameters (``$filter``, ``$select``, etc.)

        Returns:
            The parsed JSON response body as a dictionary.

        Raises:
            SAPClientError: On any transport or protocol-level failure.
        """

    @abstractmethod
    def odata_post(
        self,
        service: str,
        entity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a POST request against an OData service entity.

        Args:
            service: The OData service name.
            entity: The entity set to post to.
            payload: The request body as a dictionary.

        Returns:
            The parsed JSON response body as a dictionary.

        Raises:
            SAPClientError: On any transport or protocol-level failure.
        """

    @abstractmethod
    def bapi_call(
        self,
        function_module: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Invoke a SAP BAPI or RFC function module.

        Args:
            function_module: The name of the BAPI/RFC function module.
            params: Import and table parameters for the function module.

        Returns:
            The export and return parameters as a dictionary.
            Always contains a ``RETURN`` key with a list of return messages.

        Raises:
            SAPClientError: On any transport or protocol-level failure.
        """
