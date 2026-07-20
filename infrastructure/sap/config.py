"""SAPConfig — SAP connection settings loaded exclusively from environment.

Never hard-code credentials or endpoints. All values come from environment
variables. In development and test, ``SAP_USE_MOCK=True`` routes all SAP
calls through ``MockSAPClient`` without requiring real SAP credentials.

Required environment variables (when ``SAP_USE_MOCK`` is ``False``):
    SAP_BASE_URL      — OData base URL (e.g. https://sap.corp/sap/opu/odata/sap)
    SAP_CLIENT        — SAP client/mandant code (e.g. 100)
    SAP_USERNAME      — SAP technical user login
    SAP_PASSWORD      — SAP technical user password
    SAP_ASHOST        — SAP application server hostname (for BAPI/RFC)
    SAP_SYSNR         — SAP system number (e.g. 00)

Optional environment variables:
    SAP_TIMEOUT_SECONDS — HTTP request timeout (default: 30)
    SAP_USE_MOCK        — Use MockSAPClient instead of real SAP (default: True)
    SAP_LANG            — SAP logon language (default: EN)
    SAP_VERIFY_SSL      — Verify SAP HTTPS certificates (default: True)
    SAP_EQUIPMENT_SERVICE    — Equipment OData service (default: API_EQUIPMENT)
    SAP_EQUIPMENT_ENTITY_SET — Equipment entity set (default: Equipment)
    SAP_EQUIPMENT_PAGE_SIZE  — Page size for equipment list reads (default: 200)
    SAP_EQUIPMENT_FILTER     — Optional extra OData filter for vehicle equipment.
    SAP_EQUIPMENT_RESPONSE_FORMAT — json or xml (default: xml for Golestan view).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from django.core.exceptions import ImproperlyConfigured


@dataclass(frozen=True)
class SAPConfig:
    """Immutable SAP connection configuration.

    All fields are read from environment variables. The class enforces that
    real credentials are present when ``use_mock`` is ``False``.

    Attributes:
        base_url: SAP OData service base URL.
        client: SAP client/mandant code.
        username: SAP technical user login.
        password: SAP technical user password.
        ashost: SAP RFC application server hostname.
        sysnr: SAP RFC system number.
        timeout_seconds: HTTP timeout for OData requests.
        use_mock: When ``True``, ``MockSAPClient`` is used for all calls.
        lang: SAP logon language.
    """

    base_url: str
    client: str
    username: str
    password: str
    ashost: str
    sysnr: str
    timeout_seconds: int
    use_mock: bool
    lang: str
    verify_ssl: bool
    equipment_service: str
    equipment_entity_set: str
    equipment_page_size: int
    equipment_filter: str
    equipment_response_format: str

    @classmethod
    def from_env(cls) -> SAPConfig:
        """Build a ``SAPConfig`` from current environment variables.

        Returns:
            A populated, immutable ``SAPConfig`` instance.

        Raises:
            ImproperlyConfigured: If ``SAP_USE_MOCK`` is ``False`` but required
                credentials are missing from the environment.
        """
        use_mock = _env_bool("SAP_USE_MOCK", default=True)

        base_url = os.environ.get("SAP_BASE_URL", "")
        client = os.environ.get("SAP_CLIENT", "")
        username = os.environ.get("SAP_USERNAME", "")
        password = os.environ.get("SAP_PASSWORD", "")
        ashost = os.environ.get("SAP_ASHOST", "")
        sysnr = os.environ.get("SAP_SYSNR", "00")
        lang = os.environ.get("SAP_LANG", "EN")
        verify_ssl = _env_bool("SAP_VERIFY_SSL", default=True)
        equipment_service = os.environ.get(
            "SAP_EQUIPMENT_SERVICE", "ZC_VEHICLEDRIVER_CDS"
        )
        equipment_entity_set = os.environ.get("SAP_EQUIPMENT_ENTITY_SET", "")
        equipment_filter = os.environ.get("SAP_EQUIPMENT_FILTER", "")
        equipment_response_format = os.environ.get(
            "SAP_EQUIPMENT_RESPONSE_FORMAT", "xml"
        ).lower()
        if equipment_response_format not in {"json", "xml"}:
            raise ImproperlyConfigured(
                "SAP_EQUIPMENT_RESPONSE_FORMAT must be either 'json' or 'xml'."
            )

        try:
            timeout_seconds = int(os.environ.get("SAP_TIMEOUT_SECONDS", "30"))
        except ValueError as exc:
            raise ImproperlyConfigured(
                "SAP_TIMEOUT_SECONDS must be an integer."
            ) from exc
        try:
            equipment_page_size = int(os.environ.get("SAP_EQUIPMENT_PAGE_SIZE", "200"))
        except ValueError as exc:
            raise ImproperlyConfigured(
                "SAP_EQUIPMENT_PAGE_SIZE must be an integer."
            ) from exc
        if equipment_page_size <= 0:
            raise ImproperlyConfigured("SAP_EQUIPMENT_PAGE_SIZE must be positive.")

        if not use_mock:
            missing = [
                name
                for name, val in [
                    ("SAP_BASE_URL", base_url),
                    ("SAP_CLIENT", client),
                    ("SAP_USERNAME", username),
                    ("SAP_PASSWORD", password),
                    ("SAP_ASHOST", ashost),
                ]
                if not val
            ]
            if missing:
                raise ImproperlyConfigured(
                    f"SAP_USE_MOCK is False but the following required environment "
                    f"variables are not set: {', '.join(missing)}"
                )

        return cls(
            base_url=base_url,
            client=client,
            username=username,
            password=password,
            ashost=ashost,
            sysnr=sysnr,
            timeout_seconds=timeout_seconds,
            use_mock=use_mock,
            lang=lang,
            verify_ssl=verify_ssl,
            equipment_service=equipment_service,
            equipment_entity_set=equipment_entity_set,
            equipment_page_size=equipment_page_size,
            equipment_filter=equipment_filter,
            equipment_response_format=equipment_response_format,
        )


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("true", "1", "yes")
