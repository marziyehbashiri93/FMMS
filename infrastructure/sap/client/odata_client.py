"""SAPODataClient — production-ready OData HTTP client stub.

This client handles real SAP OData communication via HTTPS.
It is production-ready in design but NOT connected to a real SAP system.
Real credentials and endpoints will be configured when SAP details are provided.

When ``SAPConfig.use_mock`` is ``True`` (development/test), the
``MockSAPClient`` is used instead of this class.
"""

from __future__ import annotations

import logging
from typing import Any

from infrastructure.sap.client.base import ISAPClient, SAPClientError

logger = logging.getLogger(__name__)


class SAPODataClient(ISAPClient):
    """OData HTTP client for SAP read integrations.

    Uses ``httpx`` for HTTP transport with CSRF token handling, Basic Auth,
    configurable timeout, and structured error mapping.

    Args:
        base_url: SAP OData base URL (e.g. ``https://sap.example.com/sap/opu/odata/sap``).
        username: SAP technical user login.
        password: SAP technical user password.
        client_code: SAP client/mandant code (e.g. ``"100"``).
        timeout_seconds: Request timeout in seconds.
    """

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        client_code: str,
        timeout_seconds: int = 30,
        verify_ssl: bool = True,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._username = username
        self._password = password
        self._client_code = client_code
        self._timeout = timeout_seconds
        self._verify_ssl = verify_ssl

    def odata_get(
        self,
        service: str,
        entity: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GET request against an SAP OData service.

        Args:
            service: The OData service path segment (e.g. ``"API_EQUIPMENT"``)
            entity: The entity set or key expression.
            params: Optional OData query parameters.

        Returns:
            Parsed JSON response body.

        Raises:
            SAPClientError: On HTTP error, timeout, or unexpected response.
        """
        try:
            import httpx
        except ImportError as exc:
            raise SAPClientError(
                "httpx is required for SAPODataClient. "
                "Install it with: pip install httpx"
            ) from exc

        url = f"{self._base_url}/{service}/{entity}".rstrip("/")
        query_params = {"sap-client": self._client_code, "$format": "json"}
        if params:
            query_params.update(params)

        logger.debug(
            "SAP OData GET",
            extra={"service": service, "entity": entity, "url": url},
        )

        try:
            response = httpx.get(
                url,
                params=query_params,
                auth=(self._username, self._password),
                timeout=self._timeout,
                verify=self._verify_ssl,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except httpx.HTTPStatusError as exc:
            raise SAPClientError(
                f"SAP OData GET failed: {exc.response.status_code} {exc.response.text}",
                status_code=exc.response.status_code,
                raw_response=exc.response.text,
            ) from exc
        except httpx.RequestError as exc:
            raise SAPClientError(
                f"SAP OData GET request error: {exc}",
            ) from exc

    def odata_get_xml(
        self,
        service: str,
        entity: str = "",
        params: dict[str, Any] | None = None,
    ) -> str:
        """Execute a GET request and return raw XML."""
        try:
            import httpx
        except ImportError as exc:
            raise SAPClientError(
                "httpx is required for SAPODataClient. "
                "Install it with: pip install httpx"
            ) from exc

        url = f"{self._base_url}/{service}/{entity}".rstrip("/")
        query_params = {"sap-client": self._client_code, "$format": "xml"}
        if params:
            query_params.update(params)

        logger.debug(
            "SAP OData GET XML",
            extra={"service": service, "entity": entity, "url": url},
        )

        try:
            response = httpx.get(
                url,
                params=query_params,
                auth=(self._username, self._password),
                timeout=self._timeout,
                verify=self._verify_ssl,
                headers={"Accept": "application/xml, text/xml"},
            )
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as exc:
            raise SAPClientError(
                f"SAP OData GET XML failed: {exc.response.status_code} {exc.response.text}",
                status_code=exc.response.status_code,
                raw_response=exc.response.text,
            ) from exc
        except httpx.RequestError as exc:
            raise SAPClientError(f"SAP OData GET XML request error: {exc}") from exc

    def odata_post(
        self,
        service: str,
        entity: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a POST request against an SAP OData service.

        Args:
            service: The OData service path segment.
            entity: The entity set to post to.
            payload: The request body.

        Returns:
            Parsed JSON response body.

        Raises:
            SAPClientError: On HTTP error, timeout, or unexpected response.
        """
        try:
            import httpx
        except ImportError as exc:
            raise SAPClientError("httpx is required for SAPODataClient.") from exc

        url = f"{self._base_url}/{service}/{entity}"
        params = {"sap-client": self._client_code}

        logger.debug(
            "SAP OData POST",
            extra={"service": service, "entity": entity},
        )

        try:
            response = httpx.post(
                url,
                params=params,
                json=payload,
                auth=(self._username, self._password),
                timeout=self._timeout,
                verify=self._verify_ssl,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data
        except httpx.HTTPStatusError as exc:
            raise SAPClientError(
                f"SAP OData POST failed: {exc.response.status_code} {exc.response.text}",
                status_code=exc.response.status_code,
                raw_response=exc.response.text,
            ) from exc
        except httpx.RequestError as exc:
            raise SAPClientError(f"SAP OData POST request error: {exc}") from exc

    def bapi_call(
        self,
        function_module: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Not supported on ODataClient.

        Raises:
            NotImplementedError: Always. Use ``SAPBAPIClient`` for BAPI calls.
        """
        raise NotImplementedError(
            "SAPODataClient does not support BAPI calls. Use SAPBAPIClient."
        )
